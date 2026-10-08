"""User persistence contract.

Routes and services depend on this protocol. ``MongoUserRepository`` is the
running application's store. ``InMemoryUserRepository`` remains the test
double so the default suite does not need Atlas.
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

    async def ensure_indexes(self) -> None:
        """Create indexes. Implementations must not drop existing data."""

    async def get_by_id(self, user_id: str) -> User | None:
        """Return the user or ``None``."""

    async def get_by_email(self, email: str) -> User | None:
        """Return the user for a normalized email, or ``None``."""

    async def add(self, user: User) -> User:
        """Insert ``user``. Raise ``DuplicateUserError`` if the email exists."""

    async def update(self, user: User) -> User:
        """Replace the stored user. Raise ``UserNotFoundError`` if the id is new."""

    async def list_users(self) -> list[User]:
        """Return every user, oldest first."""
