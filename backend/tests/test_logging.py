"""Structured log formatting."""

import json
import logging
import sys

from app.logging_config import JsonFormatter, redact_text


def test_redact_text_hides_common_secret_patterns() -> None:
    raw = "Authorization=Bearer abc.def-123 api_key=sk-live password=hunter2 AKIAIOSFODNN7EXAMPLE"

    redacted = redact_text(raw)

    assert "abc.def-123" not in redacted
    assert "sk-live" not in redacted
    assert "hunter2" not in redacted
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted
    assert "[REDACTED]" in redacted


def test_json_formatter_emits_one_object_with_request_context() -> None:
    record = logging.LogRecord(
        name="app.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request completed",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-1"
    record.method = "GET"
    record.path = "/health"
    record.status_code = 200
    record.duration_ms = 1.5

    payload = json.loads(JsonFormatter().format(record))

    assert payload["message"] == "request completed"
    assert payload["logger"] == "app.access"
    assert payload["level"] == "INFO"
    assert payload["request_id"] == "req-1"
    assert payload["path"] == "/health"
    assert payload["status_code"] == 200
    assert "timestamp" in payload


def test_json_formatter_redacts_exception_text() -> None:
    try:
        raise RuntimeError("password=supersecret")
    except RuntimeError:
        record = logging.LogRecord(
            name="app.errors",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="unhandled error",
            args=(),
            exc_info=sys.exc_info(),
        )

    payload = json.loads(JsonFormatter().format(record))

    assert payload["exception_type"] == "RuntimeError"
    assert "supersecret" not in payload["exception"]
    assert "password= [REDACTED]" in payload["exception"]
