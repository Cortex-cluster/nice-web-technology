from __future__ import annotations

from typing import Any

from menu_panel.errors import PanelServiceError
from menu_panel.logging_utils import log_backend_error, log_backend_event
from modules.attendance import AttendanceService
from utils.env import get_settings


ATTENDANCE_STATUS_MAP = {
    "present": "Present",
    "absent": "Absent",
}


class PanelAttendanceService:
    def begin_manual_mode(self) -> dict[str, Any]:
        log_backend_event("attendance.manual.snapshot", "Preparing manual attendance mode.")
        try:
            snapshot = AttendanceService().fetch_attendance_snapshot()
        except Exception as exc:
            log_backend_error("attendance.manual.snapshot", "Attendance snapshot request failed.", exc)
            raise PanelServiceError(
                "Attendance mode could not be opened. Please refresh the session and try again.",
                status_code=502,
                log_message=str(exc),
            ) from exc

        students = snapshot.get("students", [])
        if not students:
            raise PanelServiceError(
                "No students were found for today's attendance.",
                status_code=404,
            )

        return {
            "success": True,
            "student_count": len(students),
            "students": students,
        }

    def mark_student(self, student: dict[str, Any], status: str) -> dict[str, Any]:
        normalized_status = ATTENDANCE_STATUS_MAP.get(str(status).strip().lower())
        if not normalized_status:
            raise PanelServiceError("Unsupported attendance choice provided.", status_code=400)

        student_id = str(student.get("student_id", "")).strip()
        student_name = str(student.get("name", "")).strip() or student_id or "Unknown student"
        log_backend_event(
            "attendance.mark.request",
            "Attendance mark requested.",
            student_id=student_id,
            status=normalized_status,
        )

        service = AttendanceService()
        csrf_token = get_settings().csrf_token
        if not csrf_token:
            try:
                csrf_token = service.fetch_attendance_snapshot()["csrf_token"]
            except Exception as exc:
                log_backend_error("attendance.mark.csrf", "Unable to refresh attendance token.", exc)
                raise PanelServiceError(
                    "Attendance token refresh failed. Please try again.",
                    status_code=502,
                    log_message=str(exc),
                ) from exc

        try:
            result = service.mark_student(student, normalized_status, csrf_token)
        except Exception as exc:
            log_backend_error(
                "attendance.mark.error",
                "Attendance API request failed.",
                exc,
                student_id=student_id,
                status=normalized_status,
            )
            raise PanelServiceError(
                f"Attendance API failed for {student_name}. Please try again.",
                status_code=502,
                log_message=str(exc),
            ) from exc

        if not result.get("success"):
            log_backend_error(
                "attendance.mark.rejected",
                "Attendance mark could not be verified.",
                result.get("message", "Attendance verification failed."),
                student_id=student_id,
                status=normalized_status,
                verified_status=result.get("verified_status"),
            )
            raise PanelServiceError(
                f"Attendance could not be saved for {student_name}. Please choose again.",
                status_code=502,
                log_message=str(result.get("message", "Attendance verification failed.")),
            )

        log_backend_event(
            "attendance.mark.success",
            "Attendance saved successfully.",
            student_id=student_id,
            status=normalized_status,
        )
        return {
            "success": True,
            "message": result.get("message", f"{student_name} marked {normalized_status}."),
            "student": student,
            "status": normalized_status,
            "verified_status": result.get("verified_status", normalized_status),
        }

    def mark_all_present(self) -> dict[str, Any]:
        log_backend_event("attendance.all_present", "All-present attendance run started.")
        try:
            result = AttendanceService().mark_all_present()
        except Exception as exc:
            log_backend_error("attendance.all_present", "All-present attendance failed.", exc)
            raise PanelServiceError(
                "Attendance submission failed. Please refresh the session and try again.",
                status_code=502,
                log_message=str(exc),
            ) from exc

        if not result.get("success"):
            log_backend_error(
                "attendance.all_present.partial",
                "All-present attendance completed with failures.",
                total=result.get("total"),
                succeeded=result.get("succeeded"),
                failed=result.get("failed"),
            )
        else:
            log_backend_event(
                "attendance.all_present.success",
                "All-present attendance completed successfully.",
                total=result.get("total"),
            )

        return {
            "success": bool(result.get("success")),
            "message": (
                "Attendance completed successfully."
                if result.get("success")
                else "Attendance completed with some failures."
            ),
            "total": int(result.get("total", 0)),
            "succeeded": int(result.get("succeeded", 0)),
            "failed": int(result.get("failed", 0)),
        }
