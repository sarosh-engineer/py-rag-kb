"""Registration, login, and account changes.

Routes call this service. The service calls the user repository and the
password and JWT helpers. It does not read HTTP headers.
"""

import asyncio
import logging
from datetime import UTC, datetime
from uuid import uuid4

from email_validator import EmailNotValidError, validate_email

from app.config import Settings
from app.errors import AppError
from app.models.user import Role, User
from app.repositories.errors import RepositoryUnavailable
from app.repositories.user_repository import DuplicateUserError, UserNotFoundError, UserRepository
from app.security.jwt import create_access_token
from app.security.password import hash_password, validate_password, verify_password

logger = logging.getLogger("app.services.auth")

def _invalid_credentials() -> AppError:
    return AppError(
        "Invalid email or password.",
        status_code=401,
        code="invalid_credentials",
    )


class AuthService:
    """Use cases for accounts and access tokens."""

    def __init__(self, users: UserRepository, settings: Settings) -> None:
        self._users = users
        self._settings = settings

    async def register(self, email: str, password: str) -> User:
        """Create an active viewer. Callers cannot choose the role."""
        self._require_configured()
        now = datetime.now(UTC)
        user = User(
            id=uuid4().hex,
            email=email,
            password_hash=await asyncio.to_thread(hash_password, password),
            role=Role.VIEWER,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        try:
            stored = await self._users.add(user)
        except DuplicateUserError:
            raise AppError(
                "An account with that email already exists.",
                status_code=409,
                code="email_taken",
            ) from None
        except RepositoryUnavailable:
            raise _store_unavailable() from None
        logger.info("user registered", extra={"user_id": stored.id, "role": stored.role.value})
        return stored

    async def authenticate(self, email: str, password: str) -> User:
        """Return the user when the password matches an active account.

        Unknown emails, wrong passwords, and disabled accounts share one
        error. The response does not say which case happened.
        """
        self._require_configured()
        try:
            user = await self._users.get_by_email(email)
        except RepositoryUnavailable:
            raise _store_unavailable() from None
        password_hash = user.password_hash if user is not None else _dummy_password_hash()
        password_matches = await asyncio.to_thread(verify_password, password, password_hash)
        if user is None or not password_matches or not user.is_active:
            logger.info("login failed")
            raise _invalid_credentials()
        logger.info("login succeeded", extra={"user_id": user.id})
        return user

    def issue_token(self, user: User) -> str:
        return create_access_token(user_id=user.id, role=user.role, settings=self._settings)

    async def update_user(
        self,
        actor: User,
        user_id: str,
        *,
        role: Role | None,
        is_active: bool | None,
    ) -> User:
        """Apply an admin change. An admin cannot remove their own access."""
        try:
            subject = await self._users.get_by_id(user_id)
        except RepositoryUnavailable:
            raise _store_unavailable() from None
        if subject is None:
            raise AppError("User not found.", status_code=404, code="not_found")
        next_role = subject.role if role is None else role
        next_active = subject.is_active if is_active is None else is_active
        if actor.id == subject.id and (next_role is not Role.ADMIN or not next_active):
            raise AppError(
                "You cannot remove your own admin access.",
                status_code=400,
                code="cannot_change_self",
            )
        updated = subject.model_copy(
            update={
                "role": next_role,
                "is_active": next_active,
                "updated_at": datetime.now(UTC),
            }
        )
        try:
            stored = await self._users.update(updated)
        except UserNotFoundError:
            raise AppError("User not found.", status_code=404, code="not_found") from None
        except RepositoryUnavailable:
            raise _store_unavailable() from None
        logger.info(
            "user updated",
            extra={"user_id": stored.id, "actor_id": actor.id, "role": stored.role.value},
        )
        return stored

    async def ensure_bootstrap_admin(self) -> User | None:
        """Create the configured admin when that email is not already stored.

        An existing account is left unchanged. Restarting the process does
        not promote a viewer or reset a password.
        """
        email = self._settings.bootstrap_admin_email
        password = self._settings.bootstrap_admin_password
        if not email and not password:
            return None
        try:
            normalized = validate_email(email, check_deliverability=False).normalized.lower()
            validate_password(password)
        except (EmailNotValidError, ValueError) as exc:
            raise RuntimeError("Bootstrap admin email or password is invalid.") from exc
        try:
            existing = await self._users.get_by_email(normalized)
        except RepositoryUnavailable:
            raise RuntimeError("The account store is unavailable.") from None
        if existing is not None:
            logger.info("bootstrap admin email already exists", extra={"user_id": existing.id})
            return existing
        now = datetime.now(UTC)
        user = User(
            id=uuid4().hex,
            email=normalized,
            password_hash=await asyncio.to_thread(hash_password, password),
            role=Role.ADMIN,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        try:
            stored = await self._users.add(user)
        except RepositoryUnavailable:
            raise RuntimeError("The account store is unavailable.") from None
        logger.info("bootstrap admin created", extra={"user_id": stored.id})
        return stored

    def _require_configured(self) -> None:
        if not self._settings.auth_is_configured:
            raise AppError(
                "Authentication is not configured.",
                status_code=503,
                code="auth_not_configured",
            )


def _store_unavailable() -> AppError:
    return AppError(
        "The account store is unavailable.",
        status_code=503,
        code="store_unavailable",
    )


def _dummy_password_hash() -> str:
    """Hash used when the email is unknown, so verification still does real work."""
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password("not-a-user-password")
    return _DUMMY_HASH


_DUMMY_HASH: str | None = None
