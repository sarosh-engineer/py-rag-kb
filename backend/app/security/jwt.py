"""Signed access tokens.

The payload is the user id, role, token type, and timestamps. It does not
include a password, a password hash, or an email address. Authorization
still reloads the user from the repository; the role claim is not the
source of truth.
"""

from datetime import UTC, datetime, timedelta

import jwt

from app.config import Settings
from app.errors import AppError
from app.models.user import Role

_BEARER_CHALLENGE = {"WWW-Authenticate": "Bearer"}
_TOKEN_TYPE = "access"


def authentication_required() -> AppError:
    """Generic 401. The message does not say why the token failed."""
    return AppError(
        "Authentication is required.",
        status_code=401,
        code="unauthorized",
        headers=_BEARER_CHALLENGE,
    )


def auth_not_configured() -> AppError:
    return AppError(
        "Authentication is not configured.",
        status_code=503,
        code="auth_not_configured",
    )


def create_access_token(*, user_id: str, role: Role, settings: Settings) -> str:
    """Sign an access token for ``user_id``."""
    if not settings.auth_is_configured:
        raise auth_not_configured()
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": user_id,
        "role": role.value,
        "typ": _TOKEN_TYPE,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def read_access_token(token: str, settings: Settings) -> tuple[str, Role]:
    """Return ``(user_id, role_claim)`` or raise a generic 401.

    ``role_claim`` is checked for shape only. Callers authorize with the
    role stored for that user id.
    """
    if not settings.auth_is_configured:
        raise auth_not_configured()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.InvalidTokenError:
        raise authentication_required() from None

    subject = payload.get("sub")
    token_type = payload.get("typ")
    role_claim = payload.get("role")
    if not isinstance(subject, str) or not subject or token_type != _TOKEN_TYPE:
        raise authentication_required()
    try:
        role = Role(role_claim)
    except ValueError:
        raise authentication_required() from None
    return subject, role
