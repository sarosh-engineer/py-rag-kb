"""In-memory user store used when ``APP_ENV=test``.

The running application uses ``MongoUserRepository``. This class exists so
unit tests and the default pytest process do not need MongoDB Atlas.
"""

from threading import Lock

from app.models.user import User
from app.repositories.user_repository import DuplicateUserError, UserNotFoundError


class InMemoryUserRepository:
    """Dict-backed ``UserRepository`` for tests."""

    def __init__(self) -> None:
        self._users_by_id: dict[str, User] = {}
        self._ids_by_email: dict[str, str] = {}
        self._lock = Lock()

    async def ensure_indexes(self) -> None:
        return None

    async def get_by_id(self, user_id: str) -> User | None:
        with self._lock:
            return self._users_by_id.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        with self._lock:
            user_id = self._ids_by_email.get(email)
            if user_id is None:
                return None
            return self._users_by_id.get(user_id)

    async def add(self, user: User) -> User:
        with self._lock:
            if user.email in self._ids_by_email:
                raise DuplicateUserError(user.email)
            self._users_by_id[user.id] = user
            self._ids_by_email[user.email] = user.id
            return user

    async def update(self, user: User) -> User:
        with self._lock:
            current = self._users_by_id.get(user.id)
            if current is None:
                raise UserNotFoundError(user.id)
            if current.email != user.email:
                raise ValueError("Email cannot be changed.")
            self._users_by_id[user.id] = user
            return user

    async def list_users(self) -> list[User]:
        with self._lock:
            return sorted(self._users_by_id.values(), key=lambda item: (item.created_at, item.id))
