from __future__ import annotations

from datetime import datetime
from typing import Any

from menu_panel.errors import PanelServiceError
from menu_panel.logging_utils import log_backend_error, log_backend_event
from menu_panel.paths import STUDENT_CACHE_FILE
from modules.fetch_students import StudentFetcher


class StudentCacheService:
    def fetch_students(self) -> dict[str, Any]:
        log_backend_event("students.fetch", "Student cache refresh requested.")
        try:
            result = StudentFetcher().fetch_all_students()
        except Exception as exc:
            log_backend_error("students.fetch", "Student cache refresh failed.", exc)
            raise PanelServiceError(
                "Student sync failed. Please verify the NiceWeb session and try again.",
                status_code=502,
                log_message=str(exc),
            ) from exc

        overview = self.get_cache_overview()
        log_backend_event(
            "students.fetch.success",
            "Student cache refresh completed.",
            total_students=result.get("total_students", 0),
            total_courses=result.get("total_courses", 0),
            errors=len(result.get("errors", [])),
        )
        return {
            "success": True,
            "message": "Student cache refreshed successfully.",
            "total_students": int(result.get("total_students", 0)),
            "total_courses": int(result.get("total_courses", 0)),
            "errors": result.get("errors", []),
            "duration_seconds": result.get("duration_seconds", 0),
            "last_sync_time": overview["last_sync_time"],
        }

    def get_cache_overview(self) -> dict[str, Any]:
        count = StudentFetcher().cache_count()
        if not STUDENT_CACHE_FILE.exists():
            return {
                "count": 0,
                "status": "missing",
                "last_sync_time": "Never",
            }

        last_sync_time = datetime.fromtimestamp(STUDENT_CACHE_FILE.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        if count == 0:
            return {
                "count": 0,
                "status": "empty",
                "last_sync_time": last_sync_time,
            }

        return {
            "count": count,
            "status": "ready",
            "last_sync_time": last_sync_time,
        }
