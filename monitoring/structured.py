"""Small, stdout-based structured logger for Railway service logs.

Railway parses one-line JSON written to stdout and exposes the fields in its
Log Explorer.  This module intentionally has no external dependency so a
logging failure cannot add another runtime dependency to the API service.
"""

from __future__ import annotations

import json
import os
import re
import sys
import traceback
from datetime import UTC, datetime
from threading import RLock
from typing import Any, TextIO

_LOG_LOCK = RLock()
_ALLOWED_LEVELS = {"debug", "info", "warn", "error"}
_SENSITIVE_KEY = re.compile(
    r"(?:api[_-]?key|authorization|cookie|password|prompt|question|answer|"
    r"content|history|secret|token|credential|body)",
    re.IGNORECASE,
)
_CONTROL_CHARACTER = re.compile(r"[\x00-\x1f\x7f]")
_MAX_STRING_LENGTH = 2_000
_MAX_FIELD_COUNT = 48


def emit_log(
    level: str,
    event: str,
    *,
    message: str | None = None,
    stream: TextIO | None = None,
    **fields: Any,
) -> dict[str, Any]:
    """Write a bounded, single-line JSON event and return the emitted record.

    ``level`` uses Railway's recognized values.  A critical condition should
    therefore use ``level="error"`` plus ``critical=True`` and/or
    ``alertable=True`` as structured fields.
    """

    normalized_level = str(level).strip().lower()
    if normalized_level not in _ALLOWED_LEVELS:
        normalized_level = "info"

    record: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "level": normalized_level,
        "message": _safe_text(message or event, max_length=240),
        "service": _service_name(),
        "environment": _environment_name(),
        "event": _safe_text(event, max_length=120),
    }

    for key, value in list(fields.items())[:_MAX_FIELD_COUNT]:
        if _SENSITIVE_KEY.search(str(key)):
            continue
        safe_value = _safe_value(value)
        if safe_value is not _OMIT:
            record[str(key)] = safe_value

    destination = stream or sys.stdout
    serialized = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    with _LOG_LOCK:
        print(serialized, file=destination, flush=True)
    return record


def emit_exception(
    level: str,
    event: str,
    error: BaseException,
    **fields: Any,
) -> dict[str, Any]:
    """Emit an exception event with its stack trace to Railway stdout only."""

    fields.setdefault("error_type", type(error).__name__)
    fields.setdefault(
        "stacktrace",
        _safe_text("".join(traceback.format_exception(error)), max_length=12_000),
    )
    return emit_log(level, event, **fields)


class _Omit:
    pass


_OMIT = _Omit()


def _service_name() -> str:
    return _safe_text(
        os.getenv("RAILWAY_SERVICE_NAME") or os.getenv("SERVICE_NAME") or "napas-api",
        max_length=120,
    )


def _environment_name() -> str:
    return _safe_text(
        os.getenv("RAILWAY_ENVIRONMENT_NAME")
        or os.getenv("RAILWAY_ENVIRONMENT")
        or os.getenv("ENVIRONMENT")
        or "unknown",
        max_length=120,
    )


def _safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _safe_text(value)
    return _safe_text(str(value))


def _safe_text(value: object, *, max_length: int = _MAX_STRING_LENGTH) -> str:
    text = _CONTROL_CHARACTER.sub(" ", str(value))
    return text[:max_length]
