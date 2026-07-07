"""Structured logging setup for agent observability."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from itertools import count
from pathlib import Path
from typing import Any

from src.config import FullPayloadLoggingSettings, LoggingSettings

LOGGER_NAME = "skypilot"
SENSITIVE_KEYWORDS = ("api_key", "authorization", "password", "secret", "token")
LEVEL_NAMES = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
TRACE_SCHEMA_VERSION = "2026-07-07"
_SEQUENCE = count(1)


class TextFormatter(logging.Formatter):
    """Human-readable formatter for structured event records."""

    def format(self, record: logging.LogRecord) -> str:
        event = getattr(record, "event", record.getMessage())
        fields = getattr(record, "fields", {})
        field_text = _format_fields(fields)
        message = f"{record.levelname} event={event}"
        return f"{message} {field_text}" if field_text else message


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured event records."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "event": getattr(record, "event", record.getMessage()),
        }
        payload.update(getattr(record, "fields", {}))
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)


class ExactLevelFilter(logging.Filter):
    """Allow only records for one concrete logging level."""

    def __init__(self, level: int) -> None:
        super().__init__()
        self.level = level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno == self.level


def configure_logging(settings: LoggingSettings) -> logging.Logger:
    """Configure and return the project logger."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.handlers.clear()
    logger.propagate = False

    if not settings.enabled:
        logger.addHandler(logging.NullHandler())
        logger.disabled = True
        return logger

    logger.disabled = False
    configured_level = getattr(logging, settings.level)
    logger.setLevel(logging.DEBUG if settings.full_payloads.enabled else configured_level)

    formatter = JsonFormatter() if settings.format == "json" else TextFormatter()
    log_dir = _daily_log_dir(settings.directory)
    for level_name in LEVEL_NAMES:
        level = getattr(logging, level_name)
        if level < configured_level and not (
            settings.full_payloads.enabled and level == logging.DEBUG
        ):
            continue

        handler = logging.FileHandler(
            log_dir / f"{level_name.lower()}.log",
            encoding="utf-8",
        )
        handler.setLevel(level)
        handler.addFilter(ExactLevelFilter(level))
        handler.setFormatter(
            JsonFormatter()
            if settings.full_payloads.enabled and level == logging.DEBUG
            else formatter
        )
        logger.addHandler(handler)

    return logger


def get_logger() -> logging.Logger:
    """Return the project logger without mutating global logging state."""
    return logging.getLogger(LOGGER_NAME)


def log_full_payload(
    event: str,
    payload: dict[str, Any],
    *,
    context: Any = None,
    settings: FullPayloadLoggingSettings | None = None,
    kind: str,
    phase: str,
    call_id: str | None = None,
) -> None:
    """Log complete debugging payloads as JSON records."""
    payload_settings = settings or FullPayloadLoggingSettings()
    if not payload_settings.enabled:
        return

    fields = _context_fields(context)
    fields.update(payload)
    fields = sanitize_fields(fields, redact=payload_settings.redact)
    sequence = next(_SEQUENCE)
    get_logger().debug(
        event,
        extra={
            "event": event,
            "fields": {
                "debug_payload": True,
                "trace_schema_version": TRACE_SCHEMA_VERSION,
                "trace_id": _trace_id(context),
                "sequence": sequence,
                "kind": kind,
                "phase": phase,
                "call_id": call_id,
                **serialize_for_json(fields),
            },
        },
    )


def sanitize_fields(fields: dict[str, Any], *, redact: bool = True) -> dict[str, Any]:
    """Return fields safe for logs."""
    if not redact:
        return dict(fields)

    return {key: _sanitize_value(key, value) for key, value in fields.items()}


def serialize_for_json(value: Any) -> Any:
    """Return a JSON-safe representation without dropping debugging content."""
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, dict):
        return {str(key): serialize_for_json(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [serialize_for_json(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "model_dump"):
        try:
            return serialize_for_json(value.model_dump(mode="json"))
        except Exception:
            pass
    if hasattr(value, "dict"):
        try:
            return serialize_for_json(value.dict())
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        try:
            return serialize_for_json(vars(value))
        except Exception:
            pass
    return repr(value)


def _daily_log_dir(directory: str) -> Path:
    log_dir = Path(directory).expanduser() / datetime.now(UTC).date().isoformat()
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def _context_fields(context: Any) -> dict[str, Any]:
    if context is None:
        return {}

    return {
        "user_id": getattr(context, "user_id", None),
        "thread_id": getattr(context, "thread_id", None),
        "tenant_id": getattr(context, "tenant_id", None),
        "workspace_id": getattr(context, "workspace_id", None),
        "request_id": getattr(context, "request_id", None),
        "run_id": getattr(context, "run_id", None),
        "environment": getattr(context, "environment", None),
    }


def _trace_id(context: Any) -> str:
    if context is None:
        return "unknown-trace"

    for attr in ("run_id", "request_id", "thread_id"):
        value = getattr(context, attr, None)
        if value:
            return str(value)
    return f"user:{getattr(context, 'user_id', 'unknown')}"


def _sanitize_value(key: str, value: Any) -> Any:
    if _is_sensitive_key(key):
        return "[REDACTED]"

    if isinstance(value, dict):
        return sanitize_fields(value, redact=True)
    if isinstance(value, list):
        return [_sanitize_value(key, item) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_value(key, item) for item in value)
    return value


def _is_sensitive_key(key: str) -> bool:
    normalized_key = key.lower()
    return any(keyword in normalized_key for keyword in SENSITIVE_KEYWORDS)


def _format_fields(fields: dict[str, Any]) -> str:
    return " ".join(f"{key}={value}" for key, value in fields.items())


__all__ = [
    "ExactLevelFilter",
    "JsonFormatter",
    "TextFormatter",
    "configure_logging",
    "get_logger",
    "log_full_payload",
    "sanitize_fields",
    "serialize_for_json",
]
