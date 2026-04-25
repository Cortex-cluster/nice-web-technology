from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests

from auth.login import login
from utils.env import get_settings
from utils.helpers import load_json_file
from utils.logger import log_error, log_info, log_success


COURSE_IDS = [
    400, 402, 403, 404, 405, 406, 407, 408, 409, 411, 412, 413, 414, 417, 419,
    420, 421, 422, 423, 424, 427, 430, 431, 433, 440, 441, 442, 443, 444, 445,
    448, 451, 453, 454, 455, 456, 459, 460, 461, 462, 463, 464, 465, 466, 467,
    468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482,
    483, 484, 485, 486,
]


class StudentFetcher:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.api_url = f"{self.settings.niceweb_base_url.rstrip('/')}/teacher/assignments/get-students-by-course"
        self.data_file = Path(__file__).resolve().parents[1] / "data" / "students_data.json"

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

        with ThreadPoolExecutor(max_workers=self.settings.max_fetch_workers) as executor:
            future_map = {executor.submit(self.fetch_single_course, course_id): course_id for course_id in COURSE_IDS}
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
            "total_courses": len(COURSE_IDS),
            "errors": errors,
            "duration_seconds": duration,
            "output_file": str(self.data_file),
        }

    def cache_count(self) -> int:
        payload = load_json_file(self.data_file, default=[])
        return len(payload) if isinstance(payload, list) else 0
