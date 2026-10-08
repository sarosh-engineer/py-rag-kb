"""In-memory document metadata for tests."""

from threading import Lock

from app.models.document import Document
from app.repositories.document_repository import DocumentNotFoundError


class InMemoryDocumentRepository:
    """Dict-backed ``DocumentRepository``."""

    def __init__(self) -> None:
        self._documents: dict[str, Document] = {}
        self._lock = Lock()

    async def ensure_indexes(self) -> None:
        return None

    async def add(self, document: Document) -> Document:
        with self._lock:
            self._documents[document.id] = document
            return document

    async def get(self, document_id: str) -> Document | None:
        with self._lock:
            return self._documents.get(document_id)

    async def list_documents(self) -> list[Document]:
        with self._lock:
            return sorted(
                self._documents.values(),
                key=lambda item: (item.created_at, item.id),
                reverse=True,
            )

    async def update(self, document: Document) -> Document:
        with self._lock:
            if document.id not in self._documents:
                raise DocumentNotFoundError(document.id)
            self._documents[document.id] = document
            return document

    async def delete(self, document_id: str) -> None:
        with self._lock:
            if document_id not in self._documents:
                raise DocumentNotFoundError(document_id)
            del self._documents[document_id]
