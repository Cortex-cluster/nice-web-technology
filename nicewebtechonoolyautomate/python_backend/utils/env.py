from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values, load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"


@dataclass(slots=True)
class Settings:
    niceweb_base_url: str
    niceweb_username: str
    niceweb_password: str
    session_cookies: str
    csrf_token: str
    trusted_device_token: str
    gemini_api_key: str
    fastapi_host: str
    fastapi_port: int
    request_timeout: int
    max_fetch_workers: int


def load_environment() -> None:
    load_dotenv(ENV_PATH, override=True)


def get_settings() -> Settings:
    load_environment()
    values = dotenv_values(ENV_PATH)
    return Settings(
        niceweb_base_url=str(values.get("NICEWEB_BASE_URL", "https://www.nicewebtechnologies.com") or "").strip(),
        niceweb_username=str(values.get("NICEWEB_USERNAME", "") or "").strip(),
        niceweb_password=str(values.get("NICEWEB_PASSWORD", "") or "").strip(),
        session_cookies=str(values.get("SESSION_COOKIES", "") or "").strip(),
        csrf_token=str(values.get("CSRF_TOKEN", "") or "").strip(),
        trusted_device_token=str(values.get("TRUSTED_DEVICE_TOKEN", "") or "").strip(),
        gemini_api_key=str(values.get("GEMINI_API_KEY", "") or "").strip(),
        fastapi_host=str(values.get("FASTAPI_HOST", "127.0.0.1") or "").strip(),
        fastapi_port=int(values.get("FASTAPI_PORT", 8000) or 8000),
        request_timeout=int(values.get("REQUEST_TIMEOUT", 30) or 30),
        max_fetch_workers=int(values.get("MAX_FETCH_WORKERS", 20) or 20),
    )


def update_env_values(updates: dict[str, str]) -> None:
    current = dotenv_values(ENV_PATH)
    merged = {**current, **updates}
    lines = [f"{key}={value if value is not None else ''}" for key, value in merged.items()]
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    load_environment()
