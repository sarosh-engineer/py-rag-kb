"""User persistence contract.

Routes and services depend on this protocol. ``InMemoryUserRepository`` is
the Phase 2 implementation. A MongoDB repository can replace it later by
implementing the same methods.
"""

from typing import Protocol, runtime_checkable

from app.models.user import User


class DuplicateUserError(Exception):
    """Raised when an email is already stored."""


class UserNotFoundError(Exception):
    """Raised when an update targets a missing id."""


@runtime_checkable
class UserRepository(Protocol):
    """Storage operations authentication needs. No HTTP types."""

    def get_by_id(self, user_id: str) -> User | None:
        """Return the user or ``None``."""

    def get_by_email(self, email: str) -> User | None:
        """Return the user for a normalized email, or ``None``."""

    def add(self, user: User) -> User:
        """Insert ``user``. Raise ``DuplicateUserError`` if the email exists."""

    def update(self, user: User) -> User:
        """Replace the stored user. Raise ``UserNotFoundError`` if the id is new."""

    def list_users(self) -> list[User]:
        """Return every user, oldest first."""
