"""Process-local user store.

TEMPORARY. This is not production storage. Accounts live in this process
only and disappear on restart. There is no replication, backup, or sharing
across workers. A later phase replaces this class with a MongoDB repository
that implements ``UserRepository``. Do not add features here that would
have to be thrown away, and do not treat a green local login as durable.
"""

from threading import Lock

from app.models.user import User
from app.repositories.user_repository import DuplicateUserError, UserNotFoundError


class InMemoryUserRepository:
    """Dict-backed ``UserRepository`` for development and tests."""

    def __init__(self) -> None:
        self._users_by_id: dict[str, User] = {}
        self._ids_by_email: dict[str, str] = {}
        self._lock = Lock()

    def get_by_id(self, user_id: str) -> User | None:
        with self._lock:
            return self._users_by_id.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        with self._lock:
            user_id = self._ids_by_email.get(email)
            if user_id is None:
                return None
            return self._users_by_id.get(user_id)

    def add(self, user: User) -> User:
        with self._lock:
            if user.email in self._ids_by_email:
                raise DuplicateUserError(user.email)
            self._users_by_id[user.id] = user
            self._ids_by_email[user.email] = user.id
            return user

    def update(self, user: User) -> User:
        with self._lock:
            current = self._users_by_id.get(user.id)
            if current is None:
                raise UserNotFoundError(user.id)
            if current.email != user.email:
                raise ValueError("Email cannot be changed in this phase.")
            self._users_by_id[user.id] = user
            return user

    def list_users(self) -> list[User]:
        with self._lock:
            return sorted(self._users_by_id.values(), key=lambda item: (item.created_at, item.id))
