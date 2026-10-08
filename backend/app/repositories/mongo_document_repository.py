"""MongoDB documents collection.

The application id is ``_id``. Indexes are created in place and existing
rows are left untouched.
"""

from datetime import datetime
from typing import Any

from pymongo.errors import PyMongoError

from app.models.document import Document, DocumentStatus
from app.models.user import Role
from app.repositories.document_repository import DocumentNotFoundError
from app.repositories.errors import RepositoryUnavailable


def document_to_document(document: Document) -> dict[str, Any]:
    return {
        "_id": document.id,
        "original_filename": document.original_filename,
        "s3_key": document.s3_key,
        "content_type": document.content_type,
        "size_bytes": document.size_bytes,
        "uploaded_by": document.uploaded_by,
        "owner_id": document.owner_id,
        "allowed_roles": [role.value for role in document.allowed_roles],
        "allowed_user_ids": list(document.allowed_user_ids),
        "tenant_id": document.tenant_id,
        "status": document.status.value,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }


def document_from_document(raw: dict[str, Any]) -> Document:
    return Document(
        id=str(raw["_id"]),
        original_filename=str(raw["original_filename"]),
        s3_key=str(raw["s3_key"]),
        content_type=str(raw["content_type"]),
        size_bytes=int(raw["size_bytes"]),
        uploaded_by=str(raw["uploaded_by"]),
        owner_id=str(raw["owner_id"]),
        allowed_roles=[Role(role) for role in raw.get("allowed_roles", [])],
        allowed_user_ids=[str(user_id) for user_id in raw.get("allowed_user_ids", [])],
        tenant_id=raw.get("tenant_id"),
        status=DocumentStatus(str(raw["status"])),
        created_at=_as_datetime(raw["created_at"]),
        updated_at=_as_datetime(raw["updated_at"]),
    )


class MongoDocumentRepository:
    """``DocumentRepository`` backed by the ``documents`` collection."""

    def __init__(self, collection: Any) -> None:
        self._collection = collection

    async def ensure_indexes(self) -> None:
        try:
            await self._collection.create_index("uploaded_by")
            await self._collection.create_index("owner_id")
        except PyMongoError as exc:
            raise RepositoryUnavailable from exc

    async def add(self, document: Document) -> Document:
        try:
            await self._collection.insert_one(document_to_document(document))
        except PyMongoError as exc:
            raise RepositoryUnavailable from exc
        return document

    async def get(self, document_id: str) -> Document | None:
        try:
            raw = await self._collection.find_one({"_id": document_id})
        except PyMongoError as exc:
            raise RepositoryUnavailable from exc
        return document_from_document(raw) if raw else None

    async def list_documents(self) -> list[Document]:
        try:
            cursor = self._collection.find({}).sort([("created_at", -1), ("_id", 1)])
            return [document_from_document(raw) async for raw in cursor]
        except PyMongoError as exc:
            raise RepositoryUnavailable from exc

    async def update(self, document: Document) -> Document:
        try:
            payload = document_to_document(document)
            payload.pop("_id", None)
            result = await self._collection.update_one({"_id": document.id}, {"$set": payload})
        except PyMongoError as exc:
            raise RepositoryUnavailable from exc
        if result.matched_count == 0:
            raise DocumentNotFoundError(document.id)
        return document

    async def delete(self, document_id: str) -> None:
        try:
            result = await self._collection.delete_one({"_id": document_id})
        except PyMongoError as exc:
            raise RepositoryUnavailable from exc
        if result.deleted_count == 0:
            raise DocumentNotFoundError(document_id)


def _as_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    raise RepositoryUnavailable
