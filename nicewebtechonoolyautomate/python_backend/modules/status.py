from __future__ import annotations

from modules.fetch_students import StudentFetcher
from utils.env import get_settings
from utils.logger import build_status_table, get_console


class StatusService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.console = get_console()

    def get_status(self, whatsapp_authenticated: bool) -> dict[str, object]:
        fetcher = StudentFetcher()
        student_cache_count = fetcher.cache_count()
        payload = {
            "whatsapp_authenticated": whatsapp_authenticated,
            "backend_reachable": True,
            "session_cookies": bool(self.settings.session_cookies),
            "trusted_device": bool(self.settings.trusted_device_token),
            "csrf_token": bool(self.settings.csrf_token),
            "gemini_api_key": bool(self.settings.gemini_api_key),
            "student_cache_count": student_cache_count,
            "login_ready": bool(self.settings.niceweb_username and self.settings.niceweb_password),
        }
        table = build_status_table(
            [
                ("WhatsApp Authenticated", "Yes" if payload["whatsapp_authenticated"] else "No"),
                ("Backend Reachable", "Yes"),
                ("Session Cookies", "Available" if payload["session_cookies"] else "Missing"),
                ("Trusted Device", "Available" if payload["trusted_device"] else "Missing"),
                ("CSRF Token", "Available" if payload["csrf_token"] else "Missing"),
                ("Gemini API Key", "Configured" if payload["gemini_api_key"] else "Missing"),
                ("Student Cache Count", str(student_cache_count)),
                ("Login Ready", "Yes" if payload["login_ready"] else "No"),
            ]
        )
        self.console.print(table)
        return payload
