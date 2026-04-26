from __future__ import annotations

import json
import logging
from typing import Any

from .paths import LOG_DIR


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def ensure_log_files() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    for file_name in ("backend.log", "errors.log", "whatsapp.log"):
        (LOG_DIR / file_name).touch(exist_ok=True)


def _build_logger(name: str, file_name: str, level: int) -> logging.Logger:
    ensure_log_files()
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    logger.propagate = False

    handler = logging.FileHandler(LOG_DIR / file_name, encoding="utf-8")
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(handler)
    return logger


backend_logger = _build_logger("menu_panel.backend", "backend.log", logging.INFO)
error_logger = _build_logger("menu_panel.errors", "errors.log", logging.ERROR)


def _format_context(context: dict[str, Any]) -> str:
    if not context:
        return ""
    try:
        return f" | context={json.dumps(context, ensure_ascii=False, default=str, sort_keys=True)}"
    except TypeError:
        safe_context = {key: str(value) for key, value in context.items()}
        return f" | context={json.dumps(safe_context, ensure_ascii=False, sort_keys=True)}"


def log_backend_event(action: str, message: str, **context: Any) -> None:
    backend_logger.info("%s | %s%s", action, message, _format_context(context))


def log_backend_error(action: str, message: str, error: Exception | str | None = None, **context: Any) -> None:
    if error is not None:
        context = {
            **context,
            "error_type": type(error).__name__ if isinstance(error, Exception) else "Error",
            "error": str(error),
        }
    error_logger.error("%s | %s%s", action, message, _format_context(context))
