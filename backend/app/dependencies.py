"""FastAPI dependencies shared by route modules.

Settings stay here. Authentication and role checks live in
``app.security.authorization`` so token parsing is not mixed with generic
application wiring.
"""

from typing import Annotated

from fastapi import Depends, Request

from app.config import Settings
from app.repositories.document_repository import DocumentRepository
from app.storage.object_storage import ObjectStorage


def get_settings(request: Request) -> Settings:
    """Return the settings bound to this application instance."""
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        raise RuntimeError("Application settings are not initialized")
    return settings


SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_document_repository(request: Request) -> DocumentRepository:
    """Return the document metadata store bound to this application."""
    repository = getattr(request.app.state, "document_repository", None)
    if not isinstance(repository, DocumentRepository):
        raise RuntimeError("Document repository is not initialized")
    return repository


def get_object_storage(request: Request) -> ObjectStorage:
    """Return the object store bound to this application."""
    storage = getattr(request.app.state, "object_storage", None)
    if not isinstance(storage, ObjectStorage):
        raise RuntimeError("Object storage is not initialized")
    return storage


DocumentRepositoryDep = Annotated[DocumentRepository, Depends(get_document_repository)]
ObjectStorageDep = Annotated[ObjectStorage, Depends(get_object_storage)]
