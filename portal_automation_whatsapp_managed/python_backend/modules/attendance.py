from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import unquote
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from auth.login import login
from utils.env import get_settings, update_env_values
from utils.helpers import build_authenticated_session
from utils.logger import log_error, log_info, log_success
from utils.session_recovery import is_session_expired, handle_session_expiration
from utils.token_manager import ensure_csrf_token_valid, validate_post_response


@dataclass(slots=True)
class AttendanceStudent:
    student_id: str
    name: str
    batch: str


class AttendanceService:
    VALID_STATUSES = {"Present", "Absent"}

    def __init__(self) -> None:
        self.settings = get_settings()
        self.attendance_url = f"{self.settings.niceweb_base_url.rstrip('/')}/teacher/attendance"
        self.mark_url = f"{self.settings.niceweb_base_url.rstrip('/')}/teacher/attendance/mark"

    def _build_session(self):
        if not self.settings.session_cookies:
            result = login()
            if not result["success"]:
                raise RuntimeError(result["message"])
            self.settings = get_settings()
        return build_authenticated_session(self.settings)

    @staticmethod
    def _student_id(student: dict[str, str]) -> str:
        return str(student.get("student_id") or student.get("id") or "").strip()

    @staticmethod
    def _student_name(student: dict[str, str]) -> str:
        return str(student.get("name") or student.get("student_name") or "").strip()

    @staticmethod
    def _normalize_status(value: str | None) -> str:
        normalized = (value or "").strip().lower()
        if normalized in {"1", "present", "p"}:
            return "Present"
        if normalized in {"0", "absent", "a"}:
            return "Absent"
        return ""

    def _extract_row_status(self, row: Any) -> str:
        checked_input = row.select_one(
            'input[type="radio"][name*="status"]:checked, '
            'input[type="checkbox"][name*="status"]:checked'
        )
        if checked_input:
            status = self._normalize_status(checked_input.get("value"))
            if status:
                return status

        status_select = row.find("select", {"name": "status"})
        selected_option = status_select.find("option", selected=True) if status_select else None
        if selected_option:
            status = self._normalize_status(selected_option.get("value") or selected_option.get_text(strip=True))
            if status:
                return status

        for candidate in row.find_all(["input", "option"]):
            if candidate.has_attr("checked") or candidate.has_attr("selected"):
                status = self._normalize_status(candidate.get("value") or candidate.get_text(strip=True))
                if status:
                    return status

        row_text = " ".join(row.stripped_strings)
        text_lower = row_text.lower()
        if "present" in text_lower and "absent" not in text_lower:
            return "Present"
        if "absent" in text_lower and "present" not in text_lower:
            return "Absent"
        return ""

    def _parse_attendance_snapshot(self, html: str) -> dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")
        csrf_input = soup.find("input", {"name": "_token"})
        csrf_token = csrf_input.get("value", "").strip() if csrf_input else ""
        if not csrf_token:
            raise RuntimeError("Attendance CSRF token was not found. The session may be expired.")

        students: list[AttendanceStudent] = []
        student_statuses: dict[str, str] = {}
        for row in soup.select("#attendanceTable tbody tr"):
            if "table-info" in row.get("class", []):
                continue
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            student_id = cells[0].get_text(strip=True)
            name = cells[1].get_text(strip=True)
            batch_select = row.find("select", {"name": "batch"})
            selected_option = batch_select.find("option", selected=True) if batch_select else None
            batch = selected_option.get("value", "").strip() if selected_option else "08:00 AM"
            status = self._extract_row_status(row)
            if student_id and name:
                students.append(AttendanceStudent(student_id=student_id, name=name, batch=batch))
                if status:
                    student_statuses[student_id] = status

        return {
            "csrf_token": csrf_token,
            "count": len(students),
            "students": [asdict(student) for student in students],
            "student_statuses": student_statuses,
        }

    def fetch_attendance_snapshot(self) -> dict[str, Any]:
        session = self._build_session()

        try:
            response = session.get(self.attendance_url, timeout=self.settings.request_timeout)
            log_info(f"GET {self.attendance_url} -> {response.status_code}")

            # Check for session expiration
            if is_session_expired(response):
                log_info("Session expired during attendance snapshot fetch, attempting recovery")
                handle_session_expiration()
                # Refresh settings after re-login
                self.settings = get_settings()
                session = self._build_session()
                # Retry request
                response = session.get(self.attendance_url, timeout=self.settings.request_timeout)
                log_info(f"GET {self.attendance_url} (retry) -> {response.status_code}")

            response.raise_for_status()
        except Exception as exc:
            log_error(f"Failed to fetch attendance page: {exc}")
            raise

        snapshot = self._parse_attendance_snapshot(response.text)
        update_env_values({"CSRF_TOKEN": snapshot["csrf_token"]})
        return snapshot

    def mark_student(self, student: dict[str, str], status: str, csrf_token: str) -> dict[str, Any]:
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Unsupported attendance status: {status}")

        student_id = self._student_id(student)
        if not student_id:
            raise ValueError("student_id is required to mark attendance.")

        session = self._build_session()

        # Validate and ensure CSRF token is valid
        try:
            csrf_token = ensure_csrf_token_valid(session, self.attendance_url)
            log_info(f"CSRF token validated for marking {student_id}")
        except Exception as exc:
            log_error(f"CSRF token validation failed for student {student_id}: {exc}")
            csrf_token_provided = csrf_token  # Use provided token as fallback
            log_info(f"Using provided CSRF token as fallback for {student_id}")

        xsrf_token = session.cookies.get("XSRF-TOKEN", "")
        payload = {
            "_token": csrf_token,
            "student_id": student_id,
            "batch": str(student.get("batch", "")).strip() or "08:00 AM",
            "status": status,
        }

        try:
            response = session.post(
                self.mark_url,
                data=urlencode(payload),
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": self.attendance_url,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    **({"X-XSRF-TOKEN": unquote(xsrf_token)} if xsrf_token else {}),
                },
                timeout=self.settings.request_timeout,
                allow_redirects=False,
            )
            log_info(f"POST {self.mark_url} -> {response.status_code}")

            # Check for session expiration
            if is_session_expired(response):
                log_info(f"Session expired while marking student {student_id}, attempting recovery")
                handle_session_expiration()
                self.settings = get_settings()
                session = self._build_session()
                # Retry the request
                response = session.post(
                    self.mark_url,
                    data=urlencode(payload),
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Referer": self.attendance_url,
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        **({"X-XSRF-TOKEN": unquote(xsrf_token)} if xsrf_token else {}),
                    },
                    timeout=self.settings.request_timeout,
                    allow_redirects=False,
                )
                log_info(f"POST {self.mark_url} (retry) -> {response.status_code}")

            # Check for CSRF token errors
            if not validate_post_response(response):
                log_error(f"CSRF token error detected for student {student_id}")

        except Exception as exc:
            log_error(f"Failed to mark student {student_id}: {exc}")
            return {
                "success": False,
                "student": student,
                "status": status,
                "status_code": 0,
                "response_preview": str(exc),
                "message": f"Error marking attendance: {str(exc)}",
                "verified_status": "",
                "verification_count": None,
            }

        verification_snapshot: dict[str, Any] | None = None
        verified_status = ""
        if response.status_code in {200, 201, 302}:
            try:
                verify_response = session.get(self.attendance_url, timeout=self.settings.request_timeout)
                log_info(f"VERIFY GET {self.attendance_url} -> {verify_response.status_code}")

                # Check for session expiration during verification
                if is_session_expired(verify_response):
                    log_warning(f"Session expired during verification for {student_id}")
                else:
                    verify_response.raise_for_status()
                    verification_snapshot = self._parse_attendance_snapshot(verify_response.text)
                    update_env_values({"CSRF_TOKEN": verification_snapshot["csrf_token"]})
                    self.settings = get_settings()
                    verified_status = verification_snapshot["student_statuses"].get(student_id, "")
            except Exception as exc:
                log_error(f"Verification failed for student {student_id}: {exc}")

        success = verified_status == status
        if success:
            log_success(f"{self._student_name(student) or student_id} marked {status}.")

        return {
            "success": success,
            "student": student,
            "status": status,
            "status_code": response.status_code,
            "response_preview": response.text[:500],
            "message": (
                f"Attendance verified as {status}."
                if success
                else (
                    f"Attendance not saved. Expected {status}, but page shows "
                    f"{verified_status or 'no recorded status'}."
                )
            ),
            "verified_status": verified_status,
            "verification_count": verification_snapshot["count"] if verification_snapshot else None,
        }

    def mark_all_present(self) -> dict[str, Any]:
        snapshot = self.fetch_attendance_snapshot()
        results = [self.mark_student(student, "Present", snapshot["csrf_token"]) for student in snapshot["students"]]
        succeeded = sum(1 for item in results if item["success"])
        return {
            "success": succeeded == len(results),
            "total": len(results),
            "succeeded": succeeded,
            "failed": len(results) - succeeded,
            "results": results,
        }
