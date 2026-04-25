from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests


def parse_cookie_string(cookie_string: str) -> dict[str, str]:
    cookies: dict[str, str] = {}
    for chunk in cookie_string.split(";"):
        chunk = chunk.strip()
        if "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key:
            cookies[key] = value
    return cookies


def format_cookie_dict(cookies: dict[str, str]) -> str:
    return "; ".join(f"{key}={value}" for key, value in cookies.items() if key and value)


def load_json_file(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def current_date_string() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def current_time_string() -> str:
    return datetime.now().strftime("%H:%M")


def next_saturday_string() -> str:
    today = datetime.now()
    days_until_saturday = (5 - today.weekday()) % 7
    if days_until_saturday == 0:
        days_until_saturday = 7
    return (today + timedelta(days=days_until_saturday)).strftime("%Y-%m-%d")


def build_authenticated_session(settings: Any) -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    for key, value in parse_cookie_string(settings.session_cookies).items():
        session.cookies.set(key, value, domain=".nicewebtechnologies.com", path="/")
    if settings.trusted_device_token:
        session.cookies.set(
            "nwt_trusted_device",
            settings.trusted_device_token,
            domain=".nicewebtechnologies.com",
            path="/",
        )
    return session
