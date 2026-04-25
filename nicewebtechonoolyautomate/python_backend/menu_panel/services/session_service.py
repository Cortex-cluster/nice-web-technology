from __future__ import annotations

from typing import Any

import requests

from auth.login import login as legacy_login
from menu_panel.errors import PanelServiceError
from menu_panel.logging_utils import log_backend_error, log_backend_event
from utils.env import get_settings, update_env_values
from utils.helpers import build_authenticated_session


class SessionService:
    def login(self, *, force_refresh: bool = False) -> dict[str, Any]:
        action = "session.refresh" if force_refresh else "auth.login"
        log_backend_event(action, "NiceWeb login requested.", force_refresh=force_refresh)

        if force_refresh:
            settings = get_settings()
            update_env_values(
                {
                    "SESSION_COOKIES": "",
                    "CSRF_TOKEN": "",
                    "TRUSTED_DEVICE_TOKEN": settings.trusted_device_token,
                }
            )

        result = legacy_login()
        if not result.get("success"):
            log_backend_error(action, "NiceWeb login failed.", result.get("message", "Unknown login failure."))
            raise PanelServiceError(
                "NiceWeb login failed. Please verify credentials and try again.",
                status_code=502,
                log_message=str(result.get("message", "Unknown login failure.")),
            )

        log_backend_event(
            action,
            "NiceWeb login completed.",
            has_cookies=bool(result.get("cookies")),
            has_csrf_token=bool(result.get("csrf_token")),
            has_trusted_device=bool(result.get("trusted_device_token")),
        )
        return {
            "success": True,
            "message": "NiceWeb login completed successfully.",
            "session_saved": bool(result.get("cookies")),
            "csrf_token_saved": bool(result.get("csrf_token")),
            "trusted_device_saved": bool(result.get("trusted_device_token")),
        }

    def refresh(self) -> dict[str, Any]:
        return self.login(force_refresh=True)

    def logout(self) -> dict[str, Any]:
        log_backend_event("session.logout", "Clearing persisted NiceWeb session.")
        update_env_values(
            {
                "SESSION_COOKIES": "",
                "CSRF_TOKEN": "",
                "TRUSTED_DEVICE_TOKEN": "",
            }
        )
        return {
            "success": True,
            "message": "NiceWeb session cleared. A fresh login will be required next time.",
        }

    def validate(self) -> dict[str, Any]:
        settings = get_settings()
        if not settings.session_cookies:
            return {
                "status": "missing",
                "message": "No persisted NiceWeb session is available.",
            }

        validation_url = f"{settings.niceweb_base_url.rstrip('/')}/teacher/assignments"
        try:
            session = build_authenticated_session(settings)
            response = session.get(
                validation_url,
                timeout=settings.request_timeout,
                allow_redirects=True,
            )
            final_url = str(response.url).lower()
            body = response.text.lower()

            looks_logged_in = (
                response.status_code == 200
                and "/adminlogin" not in final_url
                and "name=\"identifier\"" not in body
                and "name='identifier'" not in body
            )

            if looks_logged_in:
                return {
                    "status": "active",
                    "message": "Persisted NiceWeb session is active.",
                }

            return {
                "status": "expired",
                "message": "Persisted NiceWeb session exists but appears expired.",
            }
        except requests.RequestException as exc:
            log_backend_error("session.validate", "Session validation failed.", exc, url=validation_url)
            return {
                "status": "error",
                "message": "Unable to validate the NiceWeb session right now.",
            }
