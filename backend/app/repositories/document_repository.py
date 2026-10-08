"""Document metadata contract. Routes do not query MongoDB themselves."""

from typing import Protocol, runtime_checkable

from app.models.document import Document


class DocumentNotFoundError(Exception):
    """Raised when a document id is not stored."""


@runtime_checkable
class DocumentRepository(Protocol):
    """Metadata operations for uploaded files."""

    async def ensure_indexes(self) -> None:
        """Create indexes without dropping existing documents."""

    async def add(self, document: Document) -> Document:
        """Insert metadata."""

    async def get(self, document_id: str) -> Document | None:
        """Return one document or ``None``."""

    async def list_documents(self) -> list[Document]:
        """Return documents, newest first."""

    async def update(self, document: Document) -> Document:
        """Replace one document. Raise ``DocumentNotFoundError`` when missing."""

    async def delete(self, document_id: str) -> None:
        """Remove metadata. Raise ``DocumentNotFoundError`` when missing."""
