"""Documented error body. Handlers in ``app.errors`` produce this shape."""

from typing import Any

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    loc: list[str]
    msg: str
    type: str


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str
    details: list[ErrorDetail] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


def error_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    """OpenAPI response entries for the shared error envelope."""
    descriptions = {
        400: "The request was understood and rejected.",
        401: "Authentication is missing or was rejected.",
        403: "The account is authenticated and is not allowed to do this.",
        404: "The resource does not exist.",
        409: "The request conflicts with an existing resource.",
        422: "The request body or parameters failed validation.",
        503: "Authentication is not configured on this process.",
    }
    return {
        status: {"model": ErrorResponse, "description": descriptions.get(status, "Request failed.")}
        for status in status_codes
    }
