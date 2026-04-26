"""
CSRF token management utilities.
Handles token validation, refresh, and safe token operations.
"""

from __future__ import annotations

from typing import Any

import requests
from bs4 import BeautifulSoup

from utils.env import get_settings, update_env_values
from utils.logger import log_error, log_info, log_warning


class CSRFTokenError(Exception):
    """Raised when CSRF token operation fails."""
    pass


def get_current_csrf_token() -> str | None:
    """
    Get current CSRF token from settings.

    Returns:
        CSRF token string, or None if not available
    """
    settings = get_settings()
    token = getattr(settings, "csrf_token", None)
    if token and isinstance(token, str) and token.strip():
        return token.strip()
    return None


def token_exists() -> bool:
    """
    Check if CSRF token exists in current session.

    Returns:
        True if token exists and is non-empty, False otherwise
    """
    return bool(get_current_csrf_token())


def validate_csrf_token(token: str | None = None) -> bool:
    """
    Validate CSRF token format and existence.

    Args:
        token: Token to validate (uses current if None)

    Returns:
        True if token appears valid, False otherwise
    """
    if token is None:
        token = get_current_csrf_token()

    if not token:
        log_warning("CSRF token validation: Token is missing or empty")
        return False

    # Check token is reasonable length (Laravel CSRF tokens are ~40 chars)
    if len(token) < 20:
        log_warning(f"CSRF token validation: Token too short ({len(token)} chars)")
        return False

    if len(token) > 100:
        log_warning(f"CSRF token validation: Token too long ({len(token)} chars)")
        return False

    # Laravel tokens are alphanumeric with some special chars
    if not all(c.isalnum() or c in "_-=" for c in token):
        log_warning("CSRF token validation: Token contains invalid characters")
        return False

    log_info("CSRF token validation: Token appears valid")
    return True


def extract_csrf_token_from_html(html: str) -> str | None:
    """
    Extract CSRF token from HTML response.

    Looks for:
    - <input name="_token" value="...">
    - <meta name="csrf-token" content="...">

    Args:
        html: HTML response body

    Returns:
        CSRF token string, or None if not found
    """
    try:
        soup = BeautifulSoup(html, "html.parser")

        # Try input field first (common in Laravel forms)
        token_input = soup.find("input", {"name": "_token"})
        if token_input:
            token = token_input.get("value", "").strip()
            if token and validate_csrf_token(token):
                log_info("CSRF token extracted from input field")
                return token

        # Try meta tag (common in AJAX apps)
        token_meta = soup.find("meta", {"name": "csrf-token"})
        if token_meta:
            token = token_meta.get("content", "").strip()
            if token and validate_csrf_token(token):
                log_info("CSRF token extracted from meta tag")
                return token

        log_warning("CSRF token not found in HTML response")
        return None

    except Exception as exc:
        log_error(f"CSRF token extraction error: {exc}")
        return None


def refresh_csrf_token(
    session: requests.Session,
    url: str,
    timeout: int = 30,
) -> bool:
    """
    Refresh CSRF token by fetching a page and extracting new token.

    Args:
        session: Authenticated requests.Session
        url: URL to fetch for token extraction
        timeout: Request timeout in seconds

    Returns:
        True if refresh successful, False otherwise

    Raises:
        CSRFTokenError: If refresh fails or token invalid
    """
    try:
        log_info(f"Refreshing CSRF token from {url}")

        response = session.get(url, timeout=timeout)
        response.raise_for_status()

        new_token = extract_csrf_token_from_html(response.text)

        if not new_token:
            log_error("CSRF token refresh: No token found in response")
            raise CSRFTokenError("No CSRF token found in portal response")

        if not validate_csrf_token(new_token):
            log_error("CSRF token refresh: Extracted token failed validation")
            raise CSRFTokenError("Extracted token failed validation")

        # Update environment
        update_env_values({"CSRF_TOKEN": new_token})

        log_info("CSRF token refresh: Successfully updated token")
        return True

    except requests.RequestException as exc:
        log_error(f"CSRF token refresh: Request failed: {exc}")
        raise CSRFTokenError(f"Failed to refresh token: {exc}")
    except Exception as exc:
        log_error(f"CSRF token refresh: Unexpected error: {exc}")
        raise CSRFTokenError(f"Unexpected error during refresh: {exc}")


def ensure_csrf_token_valid(
    session: requests.Session,
    refresh_url: str | None = None,
    timeout: int = 30,
) -> str:
    """
    Ensure CSRF token is valid, refresh if needed.

    Args:
        session: Authenticated requests.Session
        refresh_url: URL to refresh token from (auto-detected if None)
        timeout: Request timeout in seconds

    Returns:
        Valid CSRF token string

    Raises:
        CSRFTokenError: If token cannot be obtained/validated
    """
    current_token = get_current_csrf_token()

    # Check if current token is valid
    if current_token and validate_csrf_token(current_token):
        log_info("CSRF token check: Current token is valid")
        return current_token

    # Token missing or invalid, try to refresh
    log_warning("CSRF token check: Token missing or invalid, attempting refresh")

    if refresh_url is None:
        settings = get_settings()
        refresh_url = f"{settings.niceweb_base_url.rstrip('/')}/teacher/assignments/add"

    try:
        refresh_csrf_token(session, refresh_url, timeout)
        new_token = get_current_csrf_token()

        if new_token:
            log_success("CSRF token ensure: Successfully obtained valid token")
            return new_token

        raise CSRFTokenError("Token refresh completed but token still invalid")

    except CSRFTokenError:
        raise
    except Exception as exc:
        log_error(f"CSRF token ensure: Unexpected error: {exc}")
        raise CSRFTokenError(f"Failed to ensure valid CSRF token: {exc}")


def validate_post_response(response: requests.Response) -> bool:
    """
    Validate POST response for CSRF-related errors.

    Checks for:
    - CSRF token mismatch
    - Token expired
    - Invalid token response

    Args:
        response: requests.Response from POST request

    Returns:
        True if response appears valid (no CSRF error), False if CSRF error detected
    """
    if response.status_code == 200:
        return True

    # CSRF token errors typically return 419 or 422
    if response.status_code in {419, 422}:
        log_warning(f"POST response: Possible CSRF error (HTTP {response.status_code})")
        return False

    # Check response body for CSRF error indicators
    body_lower = response.text.lower()
    csrf_indicators = [
        "csrf",
        "token mismatch",
        "token expired",
        "invalid token",
    ]

    for indicator in csrf_indicators:
        if indicator in body_lower:
            log_warning(f"POST response: Found CSRF indicator '{indicator}'")
            return False

    return True


# Import after class definition to avoid circular imports
log_success = None  # Will be imported properly

def __init_loggers():
    """Initialize logger functions."""
    global log_success
    from utils.logger import log_success as _log_success
    log_success = _log_success

# Call on import
__init_loggers()
