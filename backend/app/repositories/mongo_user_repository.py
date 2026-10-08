"""MongoDB users collection.

Documents use the application user id as ``_id``. The email index is unique.
``ensure_indexes`` only creates that index. It does not drop or rewrite data.
"""

from datetime import datetime
from typing import Any

from pymongo.errors import DuplicateKeyError, PyMongoError

from app.models.user import Role, User
from app.repositories.errors import RepositoryUnavailable
from app.repositories.user_repository import DuplicateUserError, UserNotFoundError


def user_to_document(user: User) -> dict[str, Any]:
    return {
        "_id": user.id,
        "email": user.email,
        "password_hash": user.password_hash,
        "role": user.role.value,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


def user_from_document(document: dict[str, Any]) -> User:
    return User(
        id=str(document["_id"]),
        email=str(document["email"]),
        password_hash=str(document["password_hash"]),
        role=Role(str(document["role"])),
        is_active=bool(document["is_active"]),
        created_at=_as_datetime(document["created_at"]),
        updated_at=_as_datetime(document["updated_at"]),
    )


class MongoUserRepository:
    """``UserRepository`` backed by the ``users`` collection."""

    def __init__(self, collection: Any) -> None:
        self._collection = collection

    async def ensure_indexes(self) -> None:
        try:
            await self._collection.create_index("email", unique=True)
        except PyMongoError as exc:
            raise RepositoryUnavailable from exc

    async def get_by_id(self, user_id: str) -> User | None:
        document = await self._find_one({"_id": user_id})
        return user_from_document(document) if document else None

    async def get_by_email(self, email: str) -> User | None:
        document = await self._find_one({"email": email})
        return user_from_document(document) if document else None

    async def add(self, user: User) -> User:
        try:
            await self._collection.insert_one(user_to_document(user))
        except DuplicateKeyError as exc:
            raise DuplicateUserError(user.email) from exc
        except PyMongoError as exc:
            raise RepositoryUnavailable from exc
        return user

    async def update(self, user: User) -> User:
        try:
            result = await self._collection.update_one(
                {"_id": user.id, "email": user.email},
                {
                    "$set": {
                        "password_hash": user.password_hash,
                        "role": user.role.value,
                        "is_active": user.is_active,
                        "updated_at": user.updated_at,
                    }
                },
            )
        except PyMongoError as exc:
            raise RepositoryUnavailable from exc
        if result.matched_count == 0:
            raise UserNotFoundError(user.id)
        return user

    async def list_users(self) -> list[User]:
        try:
            cursor = self._collection.find({}).sort([("created_at", 1), ("_id", 1)])
            return [user_from_document(document) async for document in cursor]
        except PyMongoError as exc:
            raise RepositoryUnavailable from exc

    async def _find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        try:
            return await self._collection.find_one(query)
        except PyMongoError as exc:
            raise RepositoryUnavailable from exc


def _as_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    raise RepositoryUnavailable
