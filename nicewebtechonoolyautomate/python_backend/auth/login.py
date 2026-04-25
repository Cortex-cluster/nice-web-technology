from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote

import requests

from utils.env import get_settings, update_env_values
from utils.helpers import format_cookie_dict, parse_cookie_string
from utils.logger import log_error, log_info, log_success


@dataclass(slots=True)
class LoginResult:
    success: bool
    message: str
    cookies: str = ""
    csrf_token: str = ""
    trusted_device_token: str = ""


class NiceWebAuthenticator:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
            }
        )

    @property
    def base_url(self) -> str:
        return self.settings.niceweb_base_url.rstrip("/")

    @property
    def sanctum_url(self) -> str:
        return f"{self.base_url}/sanctum/csrf-cookie"

    @property
    def login_url(self) -> str:
        return f"{self.base_url}/adminlogin"

    def _bootstrap_cookies(self) -> str:
        for key, value in parse_cookie_string(self.settings.session_cookies).items():
            self.session.cookies.set(key, value, domain=".nicewebtechnologies.com", path="/")

        if self.settings.trusted_device_token:
            self.session.cookies.set(
                "nwt_trusted_device",
                self.settings.trusted_device_token,
                domain=".nicewebtechnologies.com",
                path="/",
            )
        return self.settings.trusted_device_token

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Referer": self.base_url,
        }
        xsrf_token = self.session.cookies.get("XSRF-TOKEN", "")
        if xsrf_token:
            headers["X-XSRF-TOKEN"] = unquote(xsrf_token)
        return headers

    def _request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        response = self.session.request(
            method,
            url,
            timeout=self.settings.request_timeout,
            **kwargs,
        )
        log_info(f"{method.upper()} {url} -> {response.status_code}")
        response.raise_for_status()
        return response

    def authenticate(self) -> LoginResult:
        if not self.settings.niceweb_username or not self.settings.niceweb_password:
            return LoginResult(
                success=False,
                message="NICEWEB_USERNAME or NICEWEB_PASSWORD is missing.",
            )

        try:
            trusted_device_token = self._bootstrap_cookies()
            self._request("GET", self.base_url, headers=self._headers())
            self._request("GET", self.sanctum_url, headers=self._headers())
            self._request("GET", self.sanctum_url, headers=self._headers())

            response = self.session.post(
                self.login_url,
                json={
                    "identifier": self.settings.niceweb_username,
                    "password": self.settings.niceweb_password,
                    "nwt_trusted_device": trusted_device_token,
                },
                headers={**self._headers(), "Content-Type": "application/json"},
                timeout=self.settings.request_timeout,
            )
            log_info(f"POST {self.login_url} -> {response.status_code}")
            response.raise_for_status()

            cookie_map = self.session.cookies.get_dict()
            cookie_string = format_cookie_dict(cookie_map)
            trusted_device_token = cookie_map.get("nwt_trusted_device", trusted_device_token)
            csrf_token = cookie_map.get("XSRF-TOKEN", self.settings.csrf_token)

            if not cookie_string or "laravel_session" not in cookie_map:
                return LoginResult(
                    success=False,
                    message=(
                        "Login did not produce a Laravel session. "
                        "Verify credentials or confirm the backend flow is unchanged."
                    ),
                )

            update_env_values(
                {
                    "SESSION_COOKIES": cookie_string,
                    "CSRF_TOKEN": csrf_token,
                    "TRUSTED_DEVICE_TOKEN": trusted_device_token,
                }
            )

            log_success("Nice Web login completed and tokens were persisted.")
            return LoginResult(
                success=True,
                message="Login successful.",
                cookies=cookie_string,
                csrf_token=csrf_token,
                trusted_device_token=trusted_device_token,
            )
        except requests.RequestException as exc:
            log_error(f"Login request failed: {exc}")
            return LoginResult(success=False, message=f"Login request failed: {exc}")
        except Exception as exc:
            log_error(f"Unexpected login error: {exc}")
            return LoginResult(success=False, message=f"Unexpected login error: {exc}")


def login() -> dict[str, Any]:
    result = NiceWebAuthenticator().authenticate()
    return {
        "success": result.success,
        "message": result.message,
        "cookies": result.cookies,
        "csrf_token": result.csrf_token,
        "trusted_device_token": result.trusted_device_token,
    }
