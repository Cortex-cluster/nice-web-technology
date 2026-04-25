from __future__ import annotations

from typing import Any

from menu_panel.logging_utils import log_backend_event
from menu_panel.services.session_service import SessionService
from menu_panel.services.student_service import StudentCacheService
from utils.env import get_settings


class PanelStatusService:
    def get_status(self, whatsapp_authenticated: bool) -> dict[str, Any]:
        settings = get_settings()
        session_state = SessionService().validate()
        cache_state = StudentCacheService().get_cache_overview()

        if session_state["status"] == "active":
            niceweb_login_status = "Active"
        elif session_state["status"] == "expired":
            niceweb_login_status = "Expired"
        elif session_state["status"] == "missing":
            niceweb_login_status = "Logged Out"
        else:
            niceweb_login_status = "Validation Failed"

        if cache_state["status"] == "ready":
            student_cache_status = f"Ready ({cache_state['count']} students)"
        elif cache_state["status"] == "empty":
            student_cache_status = "Empty"
        else:
            student_cache_status = "Missing"

        payload = {
            "whatsapp_status": "Connected" if whatsapp_authenticated else "Disconnected",
            "backend_status": "Online",
            "niceweb_login_status": niceweb_login_status,
            "student_cache_status": student_cache_status,
            "last_sync_time": cache_state["last_sync_time"],
            "gemini_status": "Configured" if settings.gemini_api_key else "Missing API key",
            "login_ready": bool(settings.niceweb_username and settings.niceweb_password),
            "cache_count": cache_state["count"],
            "session_validation_status": session_state["status"],
        }
        log_backend_event("status.summary", "Status summary requested.", **payload)
        return payload
