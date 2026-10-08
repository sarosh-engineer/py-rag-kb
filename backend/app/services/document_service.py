"""Upload, list, download, and delete documents.

S3 and MongoDB are updated in an order that can be retried. A response is
successful only when both sides agree.
"""

import logging
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import UploadFile

from app.config import Settings
from app.errors import AppError
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.repositories.document_repository import DocumentNotFoundError, DocumentRepository
from app.repositories.errors import ObjectNotFoundError, RepositoryUnavailable, StorageError
from app.services.files import read_upload
from app.storage.keys import UnsafeFilenameError, build_object_key
from app.storage.object_storage import ObjectStorage

logger = logging.getLogger("app.services.documents")


class DocumentService:
    """Use cases for document bytes and metadata."""

    def __init__(
        self,
        documents: DocumentRepository,
        storage: ObjectStorage,
        settings: Settings,
    ) -> None:
        self._documents = documents
        self._storage = storage
        self._settings = settings

    async def upload(self, user: User, upload: UploadFile) -> Document:
        """Store bytes, then metadata. Remove the object if metadata fails."""
        document_id = uuid4().hex
        try:
            object_key, safe_filename = build_object_key(document_id, upload.filename)
        except UnsafeFilenameError:
            raise AppError("The filename is not allowed.", status_code=400, code="invalid_filename") from None
        body = await read_upload(upload, self._settings, safe_filename)
        content_type = (upload.content_type or "").split(";", 1)[0].strip().lower()
        try:
            await self._storage.put(object_key, body, content_type)
        except StorageError:
            raise AppError(
                "The document could not be stored.",
                status_code=503,
                code="storage_unavailable",
            ) from None
        now = datetime.now(UTC)
        document = Document(
            id=document_id,
            original_filename=safe_filename,
            s3_key=object_key,
            content_type=content_type,
            size_bytes=len(body),
            uploaded_by=user.id,
            owner_id=user.id,
            created_at=now,
            updated_at=now,
        )
        try:
            return await self._documents.add(document)
        except RepositoryUnavailable:
            await self._discard_orphan(object_key, document_id)
            raise AppError(
                "The document could not be saved.",
                status_code=503,
                code="metadata_write_failed",
            ) from None

    async def list_documents(self) -> list[Document]:
        try:
            return await self._documents.list_documents()
        except RepositoryUnavailable:
            raise AppError(
                "Documents are unavailable.",
                status_code=503,
                code="store_unavailable",
            ) from None

    async def get(self, document_id: str) -> Document:
        document = await self._load(document_id)
        return document

    async def read_content(self, document_id: str) -> tuple[Document, bytes]:
        document = await self._load(document_id)
        try:
            body = await self._storage.get(document.s3_key)
        except ObjectNotFoundError:
            raise AppError("Document not found.", status_code=404, code="object_missing") from None
        except StorageError:
            raise AppError(
                "The document could not be read.",
                status_code=503,
                code="storage_unavailable",
            ) from None
        return document, body

    async def delete(self, document_id: str) -> None:
        """Mark metadata, delete the object, then delete metadata.

        If the object delete fails, the row stays ``delete_pending`` and the
        call returns an error. If the object is gone and the row delete fails,
        the call also returns an error. A later delete retries both steps.
        Success means the row is gone.
        """
        document = await self._load(document_id)
        pending = document.model_copy(
            update={"status": DocumentStatus.DELETE_PENDING, "updated_at": datetime.now(UTC)}
        )
        try:
            await self._documents.update(pending)
        except DocumentNotFoundError:
            raise AppError("Document not found.", status_code=404, code="not_found") from None
        except RepositoryUnavailable:
            raise AppError(
                "The document could not be deleted.",
                status_code=503,
                code="store_unavailable",
            ) from None
        try:
            await self._storage.delete(document.s3_key)
        except ObjectNotFoundError:
            logger.info("object already absent", extra={"document_id": document_id})
        except StorageError:
            raise AppError(
                "The document could not be deleted.",
                status_code=503,
                code="storage_unavailable",
            ) from None
        try:
            await self._documents.delete(document_id)
        except DocumentNotFoundError:
            return None
        except RepositoryUnavailable:
            logger.info("metadata delete failed after object delete", extra={"document_id": document_id})
            raise AppError(
                "The document could not be deleted.",
                status_code=503,
                code="metadata_delete_failed",
            ) from None

    async def _load(self, document_id: str) -> Document:
        try:
            document = await self._documents.get(document_id)
        except RepositoryUnavailable:
            raise AppError(
                "Documents are unavailable.",
                status_code=503,
                code="store_unavailable",
            ) from None
        if document is None:
            raise AppError("Document not found.", status_code=404, code="not_found")
        return document

    async def _discard_orphan(self, object_key: str, document_id: str) -> None:
        try:
            await self._storage.delete(object_key)
        except ObjectNotFoundError:
            return None
        except StorageError:
            logger.info("orphan object remains", extra={"document_id": document_id})
