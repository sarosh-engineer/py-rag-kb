"""Structured logging for the API process.

Logs are written to stdout. A container or systemd unit can forward that
stream to CloudWatch later without changing application code.

This module is named ``logging_config`` so it does not shadow the standard
library ``logging`` module.

Callers must not log secrets, credentials, document contents, or raw prompts.
``redact_text`` is a best-effort guard for accidental secret strings. It is
not a substitute for keeping sensitive values out of log messages.
"""

import json
import logging
import re
import sys
from datetime import UTC, datetime
from types import TracebackType
from typing import Any

_ExcInfo = tuple[type[BaseException] | None, BaseException | None, TracebackType | None]

from app.config import Settings

_APP_HANDLER_FLAG = "_genai_rag_handler"

_SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)\bbearer\s+[a-z0-9\-._~+/]+=*"), "Bearer [REDACTED]"),
    (
        re.compile(
            r"(?i)\b(api[_-]?key|secret|password|token|authorization)\s*([=:])\s*\S+"
        ),
        r"\1\2 [REDACTED]",
    ),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED]"),
)

# Fields copied from LogRecord extras into the JSON line. Query strings are
# intentionally absent because they can carry tokens.
_CONTEXT_FIELDS = (
    "request_id",
    "method",
    "path",
    "status_code",
    "duration_ms",
    "exception_type",
)


def redact_text(value: str) -> str:
    """Replace common secret patterns with a fixed placeholder."""
    redacted = value
    for pattern, replacement in _SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


class JsonFormatter(logging.Formatter):
    """Format one log record as a single JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_text(record.getMessage()),
        }
        for field in _CONTEXT_FIELDS:
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        exc_info = _coerce_exc_info(record.exc_info)
        if exc_info and exc_info[0] is not None:
            payload["exception_type"] = exc_info[0].__name__
            payload["exception"] = redact_text(self.formatException(exc_info))
        return json.dumps(payload, default=str)


def _coerce_exc_info(exc_info: Any) -> _ExcInfo | None:
    """Return the exception triple stored on a log record.

    ``Logger.exception`` stores a tuple. A record built with ``exc_info=True``
    can still hold ``True`` until the logging module resolves it.
    """
    if exc_info is True:
        resolved = sys.exc_info()
        return resolved if resolved[0] is not None else None
    if isinstance(exc_info, tuple):
        return exc_info
    return None


def configure_logging(settings: Settings) -> None:
    """Attach one stdout handler to the root logger.

    Existing handlers owned by this application are replaced so repeated
    ``create_app`` calls do not duplicate lines. Handlers installed by pytest
    are left in place.
    """
    root = logging.getLogger()
    root.setLevel(settings.log_level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter()
        if settings.log_json
        else logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    setattr(handler, _APP_HANDLER_FLAG, True)

    for existing in list(root.handlers):
        if getattr(existing, _APP_HANDLER_FLAG, False):
            root.removeHandler(existing)
    root.addHandler(handler)
