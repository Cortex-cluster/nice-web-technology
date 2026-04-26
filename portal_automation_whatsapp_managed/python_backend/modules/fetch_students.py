from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from auth.login import login
from utils.env import get_settings
from utils.helpers import load_json_file
from utils.logger import log_error, log_info, log_success

# Fallback static course IDs in case dynamic fetch fails
FALLBACK_COURSE_IDS = [
    400, 402, 403, 404, 405, 406, 407, 408, 409, 411, 412, 413, 414, 417, 419,
    420, 421, 422, 423, 424, 427, 430, 431, 433, 440, 441, 442, 443, 444, 445,
    448, 451, 453, 454, 455, 456, 459, 460, 461, 462, 463, 464, 465, 466, 467,
    468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482,
    483, 484, 485, 486,
]


def fetch_course_ids_from_portal(session: requests.Session, base_url: str) -> list[int]:
    """
    Dynamically fetch course IDs from the portal's assignment page.

    Parses the course selection dropdown from:
    {base_url}/teacher/assignments/add

    Args:
        session: Authenticated requests.Session with portal cookies
        base_url: Base URL of NiceWeb portal (e.g., https://www.nicewebtechnologies.com)

    Returns:
        List of course IDs as integers, or empty list if fetch fails

    Logs warnings/errors if parsing fails, then falls back to static IDs
    """
    try:
        url = f"{base_url.rstrip('/')}/teacher/assignments/add"
        log_info(f"Fetching course IDs from {url}")

        response = session.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Find the course_id select dropdown
        course_select = soup.find("select", {"id": "course_id", "name": "course_id"})
        if not course_select:
            log_error("Course ID dropdown not found. HTML structure may have changed.")
            return []

        course_ids: list[int] = []
        options = course_select.find_all("option")

        if not options:
            log_error("No option elements found in course select dropdown.")
            return []

        for option in options:
            value = option.get("value", "").strip()

            # Skip empty values and placeholder options
            if not value:
                continue

            # Skip disabled placeholder options (typically "Select a course")
            if option.has_attr("disabled") or option.has_attr("selected"):
                # Check if it's a placeholder by looking at text content
                text = option.get_text(strip=True).lower()
                if text in {"select a course", "select a course..."}:
                    continue

            # Try to convert to integer
            try:
                course_id = int(value)
                course_ids.append(course_id)
            except ValueError:
                log_error(f"Failed to parse course ID '{value}' as integer. Skipping.")
                continue

        if not course_ids:
            log_error("No valid course IDs extracted from dropdown.")
            return []

        log_success(f"Successfully fetched {len(course_ids)} course IDs from portal")
        return sorted(course_ids)

    except requests.RequestException as exc:
        log_error(f"Failed to fetch course list from portal: {exc}")
        return []
    except Exception as exc:
        log_error(f"Unexpected error while parsing course IDs: {exc}")
        return []


class StudentFetcher:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.api_url = f"{self.settings.niceweb_base_url.rstrip('/')}/teacher/assignments/get-students-by-course"
        self.data_file = Path(__file__).resolve().parents[1] / "data" / "students_data.json"
        self.course_ids: list[int] = []

    def _headers(self) -> dict[str, str]:
        if not self.settings.session_cookies:
            result = login()
            if not result["success"]:
                raise RuntimeError(result["message"])
            self.settings = get_settings()

        return {
            "Cookie": self.settings.session_cookies,
            "Accept": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Referer": f"{self.settings.niceweb_base_url.rstrip('/')}/teacher/assignments",
        }

    def _get_course_ids(self) -> list[int]:
        """
        Get list of course IDs to fetch.

        Attempts to fetch dynamically from portal. Falls back to static list if:
        - Dynamic fetch fails
        - HTML structure changed
        - Parsing errors occur

        Returns:
            List of course IDs as integers
        """
        # Try dynamic fetch first
        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0"})
        from utils.helpers import parse_cookie_string

        for key, value in parse_cookie_string(self.settings.session_cookies).items():
            session.cookies.set(key, value, domain=".nicewebtechnologies.com", path="/")
        if self.settings.trusted_device_token:
            session.cookies.set(
                "nwt_trusted_device",
                self.settings.trusted_device_token,
                domain=".nicewebtechnologies.com",
                path="/",
            )

        dynamic_ids = fetch_course_ids_from_portal(session, self.settings.niceweb_base_url)

        if dynamic_ids:
            log_info(f"Using {len(dynamic_ids)} dynamically fetched course IDs")
            return dynamic_ids

        log_info(f"Using {len(FALLBACK_COURSE_IDS)} fallback static course IDs")
        return FALLBACK_COURSE_IDS

    def fetch_single_course(self, course_id: int) -> dict[str, Any]:
        response = requests.get(
            f"{self.api_url}?course_id={course_id}",
            headers=self._headers(),
            timeout=self.settings.request_timeout,
        )
        log_info(f"GET {self.api_url}?course_id={course_id} -> {response.status_code}")
        if response.status_code != 200:
            return {
                "course_id": course_id,
                "status": "error",
                "message": f"HTTP {response.status_code}",
                "students": [],
            }

        payload = response.json()
        students: list[dict[str, Any]] = []
        if isinstance(payload, list):
            for item in payload:
                students.append(
                    {
                        "student_id": str(item.get("student_id", "")).strip(),
                        "name": str(item.get("name", "")).strip(),
                        "course_id": str(item.get("course_id", "")).strip(),
                        "course_name": str(item.get("courses", "")).strip(),
                        "is_online": bool(item.get("is_online")),
                    }
                )

        return {
            "course_id": course_id,
            "status": "success" if students else "empty",
            "message": f"{len(students)} students found" if students else "No students found",
            "students": students,
        }

    def fetch_all_students(self) -> dict[str, Any]:
        started_at = time.time()
        all_students: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        # Get course IDs (dynamic or fallback)
        course_ids = self._get_course_ids()
        if not course_ids:
            log_error("No course IDs available. Cannot fetch students.")
            return {
                "success": False,
                "total_students": 0,
                "total_courses": 0,
                "errors": [{"message": "No course IDs available"}],
                "duration_seconds": 0,
                "output_file": str(self.data_file),
            }

        with ThreadPoolExecutor(max_workers=self.settings.max_fetch_workers) as executor:
            future_map = {executor.submit(self.fetch_single_course, course_id): course_id for course_id in course_ids}
            for future in as_completed(future_map):
                course_id = future_map[future]
                try:
                    result = future.result()
                    if result["status"] == "error":
                        errors.append(result)
                        log_error(f"Course {course_id}: {result['message']}")
                    else:
                        all_students.extend(result["students"])
                        log_info(f"Course {course_id}: {result['message']}")
                except Exception as exc:
                    errors.append(
                        {
                            "course_id": course_id,
                            "status": "error",
                            "message": str(exc),
                            "students": [],
                        }
                    )
                    log_error(f"Course {course_id}: {exc}")

        deduped: dict[tuple[str, str], dict[str, Any]] = {}
        for student in all_students:
            key = (student["student_id"], student["course_id"])
            deduped[key] = student

        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        self.data_file.write_text(
            json.dumps(list(deduped.values()), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        duration = round(time.time() - started_at, 2)
        log_success(f"Saved {len(deduped)} students to {self.data_file}.")
        return {
            "success": True,
            "total_students": len(deduped),
            "total_courses": len(course_ids),
            "errors": errors,
            "duration_seconds": duration,
            "output_file": str(self.data_file),
        }

    def cache_count(self) -> int:
        payload = load_json_file(self.data_file, default=[])
        return len(payload) if isinstance(payload, list) else 0
