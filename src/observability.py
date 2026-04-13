"""Structured logging helpers for chat and admin observability."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from typing import Any

_REDACTED = "[REDACTED]"
_SENSITIVE_EXACT_KEYS = {
    "admin_api_token",
    "authorization",
    "gemini_api_key",
    "openai_api_key",
}
_SENSITIVE_MARKERS = ("api_key", "secret")


def configure_logging(level_name: str) -> None:
    """Configure root logging to emit plain JSON lines to stdout."""
    logging.basicConfig(
        level=getattr(logging, level_name.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
        force=True,
    )


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    **fields: Any,
) -> None:
    """Emit a structured JSON log event through the standard logger."""
    payload = {"event": event, **_sanitize_mapping(fields)}
    logger.log(level, json.dumps(payload, default=_json_default, sort_keys=True))


def _sanitize_mapping(mapping: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in mapping.items():
        if _is_sensitive_key(key):
            sanitized[key] = _REDACTED
            continue
        sanitized[key] = _sanitize_value(value)
    return sanitized


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    if lowered in _SENSITIVE_EXACT_KEYS:
        return True
    return any(marker in lowered for marker in _SENSITIVE_MARKERS)


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _sanitize_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, str):
        return _truncate(value)
    return value


def _truncate(value: str, limit: int = 400) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
