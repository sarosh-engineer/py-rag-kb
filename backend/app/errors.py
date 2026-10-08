"""API error responses.

Clients receive a stable JSON shape and a request id. Stack traces and
exception messages stay in the server log. Validation errors omit the
submitted value so a later document upload cannot echo file contents back
to the caller through a 422 response.
"""

import logging
from typing import Any

from fastapi import Request
from starlette.exceptions import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import Settings
from app.logging_config import redact_text

logger = logging.getLogger("app.errors")


class AppError(Exception):
    """Expected application failure with a safe client message."""

    def __init__(self, message: str, *, status_code: int = 400, code: str = "bad_request") -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


def request_id_from(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, str) and request_id:
        return request_id
    return "unknown"


def error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    request_id: str,
    details: list[dict[str, Any]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
        }
    }
    if details is not None:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body, headers=headers)


def unhandled_error_headers(request: Request) -> dict[str, str]:
    """Headers for errors rendered outside the CORS middleware.

    Starlette handles unexpected exceptions in its outermost middleware, so
    the CORS middleware never sees that response. Reflect an allowed origin
    here, and always return the request id.
    """
    headers = {"X-Request-ID": request_id_from(request)}
    origin = request.headers.get("origin")
    settings = getattr(request.app.state, "settings", None)
    if origin and isinstance(settings, Settings) and origin in settings.cors_origins:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Vary"] = "Origin"
    return headers


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.info(
        "application error",
        extra={
            "request_id": request_id_from(request),
            "status_code": exc.status_code,
            "exception_type": exc.code,
        },
    )
    return error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        request_id=request_id_from(request),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) and exc.detail.strip() else "Request failed."
    return error_response(
        status_code=exc.status_code,
        code="http_error",
        message=redact_text(message),
        request_id=request_id_from(request),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = [
        {
            "loc": [str(part) for part in error.get("loc", ())],
            "msg": redact_text(str(error.get("msg", "Invalid value"))),
            "type": str(error.get("type", "value_error")),
        }
        for error in exc.errors()
    ]
    return error_response(
        status_code=422,
        code="validation_error",
        message="Request validation failed.",
        request_id=request_id_from(request),
        details=details,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "unhandled error",
        extra={
            "request_id": request_id_from(request),
            "exception_type": type(exc).__name__,
        },
    )
    return error_response(
        status_code=500,
        code="internal_error",
        message="An unexpected error occurred.",
        request_id=request_id_from(request),
        headers=unhandled_error_headers(request),
    )
