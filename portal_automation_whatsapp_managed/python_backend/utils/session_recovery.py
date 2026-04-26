"""
Session recovery utilities for detecting and handling session expiration.
Provides robust session validation and automatic re-authentication.
"""

from __future__ import annotations

import re
import time
from typing import Any

import requests

from utils.env import get_settings, update_env_values
from utils.logger import log_error, log_info, log_success, log_warning


class SessionExpiredError(Exception):
    """Raised when session is detected as expired."""
    pass


def is_session_expired(response: requests.Response) -> bool:
    """
    Detect if response indicates session expiration.

    Checks for:
    - HTTP 401 Unauthorized
    - HTTP 403 Forbidden
    - Redirect to login page
    - Portal response body indicating logout

    Args:
        response: requests.Response to check

    Returns:
        True if session appears expired, False otherwise
    """
    # Check HTTP status codes
    if response.status_code in {401, 403}:
        log_info(f"Session expired: HTTP {response.status_code}")
        return True

    # Check for redirect to login page
    if response.status_code in {301, 302, 303, 307, 308}:
        location = response.headers.get("location", "").lower()
        if "login" in location or "auth" in location:
            log_info(f"Session expired: Redirected to {location}")
            return True

    # Check for login page in response body (for 200 OK responses)
    if response.status_code == 200:
        body_lower = response.text.lower()

        # Common portal logout indicators
        logout_indicators = [
            "logged out",
            "session expired",
            "please login",
            "authentication required",
            "login.html",
            '<form.*action.*login',
        ]

        for indicator in logout_indicators:
            if re.search(indicator, body_lower):
                log_info(f"Session expired: Found '{indicator}' in response body")
                return True

    return False


def get_last_login_timestamp() -> float | None:
    """
    Get timestamp of last successful login.

    Returns:
        Unix timestamp of last login, or None if never logged in
    """
    settings = get_settings()
    try:
        return float(settings.last_login_timestamp or 0) or None
    except (ValueError, TypeError):
        return None


def update_last_login_timestamp() -> None:
    """Update last successful login timestamp to current time."""
    current_time = time.time()
    update_env_values({"LAST_LOGIN_TIMESTAMP": str(current_time)})
    log_success(f"Last login timestamp updated: {current_time}")


def handle_session_expiration(retry_count: int = 0, max_retries: int = 1) -> bool:
    """
    Handle session expiration by attempting to re-authenticate.

    Args:
        retry_count: Current retry attempt number
        max_retries: Maximum number of retry attempts (default 1)

    Returns:
        True if re-authentication succeeded, False otherwise

    Raises:
        SessionExpiredError: If max retries exceeded or re-auth fails
    """
    if retry_count > max_retries:
        log_error(f"Session recovery failed: Max retries ({max_retries}) exceeded")
        raise SessionExpiredError("Session expired and recovery failed after retries")

    log_warning(f"Session expired detected. Attempting recovery (attempt {retry_count + 1}/{max_retries + 1})")

    try:
        # Import here to avoid circular imports
        from auth.login import login

        result = login()

        if result["success"]:
            update_last_login_timestamp()
            log_success("Session recovery successful - re-authentication completed")
            return True
        else:
            log_error(f"Session recovery failed: {result['message']}")
            raise SessionExpiredError(result["message"])

    except Exception as exc:
        log_error(f"Session recovery exception: {exc}")
        raise SessionExpiredError(f"Session recovery failed: {exc}")


def auto_recover_session(func):
    """
    Decorator to automatically recover from session expiration.

    Wraps a function that makes authenticated requests and handles
    session expiration by triggering re-authentication and retry.

    Usage:
        @auto_recover_session
        def fetch_data():
            response = session.get(url)
            return response.json()

    Args:
        func: Function to wrap

    Returns:
        Wrapped function with session recovery
    """
    def wrapper(*args, **kwargs):
        retry_count = 0
        max_retries = 1

        while retry_count <= max_retries:
            try:
                return func(*args, **kwargs)
            except SessionExpiredError:
                retry_count += 1
                if retry_count <= max_retries:
                    log_warning(f"Session expired, retrying with fresh auth (attempt {retry_count})")
                    try:
                        handle_session_expiration(retry_count - 1, max_retries)
                    except SessionExpiredError:
                        pass  # Will fail in next iteration
                else:
                    raise
            except requests.RequestException as exc:
                # Check if error was due to session expiration
                if hasattr(exc, 'response') and exc.response is not None:
                    if is_session_expired(exc.response):
                        log_warning("Session expired detected in request exception")
                        retry_count += 1
                        if retry_count <= max_retries:
                            try:
                                handle_session_expiration(retry_count - 1, max_retries)
                            except SessionExpiredError:
                                pass
                        else:
                            raise SessionExpiredError(f"Session expired: {exc}")
                raise

        # Should not reach here, but handle just in case
        raise SessionExpiredError("Session recovery exhausted all retries")

    return wrapper


def validate_session(session: requests.Session | None = None, base_url: str | None = None) -> bool:
    """
    Validate that current session is still active and authenticated.

    Makes a lightweight request to verify session is valid.

    Args:
        session: Authenticated session to validate (uses current if None)
        base_url: Portal base URL (uses settings if None)

    Returns:
        True if session is valid, False if expired or invalid
    """
    try:
        if session is None:
            from utils.helpers import build_authenticated_session
            settings = get_settings()
            session = build_authenticated_session(settings)

        if base_url is None:
            base_url = get_settings().niceweb_base_url.rstrip("/")

        # Make lightweight request to check auth
        response = session.get(f"{base_url}/teacher/dashboard", timeout=10)

        if is_session_expired(response):
            log_warning("Session validation failed: Session appears expired")
            return False

        if response.status_code == 200:
            log_info("Session validation successful: Session is active")
            return True

        log_warning(f"Session validation unclear: HTTP {response.status_code}")
        return False

    except Exception as exc:
        log_error(f"Session validation error: {exc}")
        return False

