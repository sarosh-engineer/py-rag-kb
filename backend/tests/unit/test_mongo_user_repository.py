"""Mongo user repository against an in-memory collection, not Atlas."""

import asyncio
from datetime import UTC, datetime

import pytest

from app.models.user import Role, User
from app.repositories.mongo_user_repository import MongoUserRepository
from app.repositories.user_repository import DuplicateUserError


class _Cursor:
    def __init__(self, documents: list[dict]) -> None:
        self._documents = documents

    def sort(self, spec: list[tuple[str, int]]) -> "_Cursor":
        for key, direction in reversed(spec):
            self._documents.sort(key=lambda item: item.get(key), reverse=direction < 0)
        return self

    def __aiter__(self) -> "_Cursor":
        self._index = 0
        return self

    async def __anext__(self) -> dict:
        if self._index >= len(self._documents):
            raise StopAsyncIteration
        item = self._documents[self._index]
        self._index += 1
        return item


class _Result:
    def __init__(self, matched: int = 0, deleted: int = 0) -> None:
        self.matched_count = matched
        self.deleted_count = deleted


class FakeUsers:
    """Small stand-in for an async PyMongo collection."""

    def __init__(self) -> None:
        self.docs: dict[str, dict] = {}

    async def create_index(self, key: str, unique: bool = False) -> str:
        assert key == "email"
        assert unique is True
        return key

    async def insert_one(self, document: dict) -> None:
        if document["_id"] in self.docs or any(
            item.get("email") == document.get("email") for item in self.docs.values()
        ):
            from pymongo.errors import DuplicateKeyError

            raise DuplicateKeyError("duplicate")
        self.docs[document["_id"]] = dict(document)

    async def find_one(self, query: dict) -> dict | None:
        for document in self.docs.values():
            if all(document.get(key) == value for key, value in query.items()):
                return dict(document)
        return None

    async def update_one(self, query: dict, update: dict) -> _Result:
        for document in self.docs.values():
            if all(document.get(key) == value for key, value in query.items()):
                document.update(update["$set"])
                return _Result(matched=1)
        return _Result(matched=0)

    def find(self, query: dict | None = None) -> _Cursor:
        del query
        return _Cursor(list(self.docs.values()))


def _user(email: str = "viewer@example.com", *, active: bool = True) -> User:
    now = datetime.now(UTC)
    return User(
        id="user-1",
        email=email,
        password_hash="$argon2id$stored-hash",
        role=Role.VIEWER,
        is_active=active,
        created_at=now,
        updated_at=now,
    )


def test_user_round_trip_keeps_hash_role_and_active_flag() -> None:
    repository = MongoUserRepository(FakeUsers())

    async def scenario():
        await repository.ensure_indexes()
        created = _user(active=False)
        await repository.add(created)
        return created, await repository.get_by_email(created.email)

    created, loaded = asyncio.run(scenario())

    assert loaded is not None
    assert loaded.id == created.id
    assert loaded.password_hash == created.password_hash
    assert loaded.role is Role.VIEWER
    assert loaded.is_active is False
    assert loaded.password_hash != "plaintext"


def test_duplicate_email_is_rejected() -> None:
    repository = MongoUserRepository(FakeUsers())

    async def scenario() -> None:
        await repository.add(_user())
        with pytest.raises(DuplicateUserError):
            await repository.add(_user().model_copy(update={"id": "user-2"}))

    asyncio.run(scenario())


def test_lookup_and_role_update_persist() -> None:
    repository = MongoUserRepository(FakeUsers())

    async def scenario():
        created = _user()
        await repository.add(created)
        updated = created.model_copy(update={"role": Role.EDITOR, "updated_at": datetime.now(UTC)})
        await repository.update(updated)
        loaded = await repository.get_by_id(created.id)
        missing = await repository.get_by_email("missing@example.com")
        return loaded, missing

    loaded, missing = asyncio.run(scenario())
    assert loaded is not None
    assert loaded.role is Role.EDITOR
    assert missing is None
