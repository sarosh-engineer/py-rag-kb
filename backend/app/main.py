"""FastAPI application factory.

``create_app`` builds a fully configured application. The module-level
``app`` object is what ``uvicorn app.main:app`` serves. Tests call
``create_app`` with an explicit ``Settings`` instance so they do not depend
on the developer machine's environment.

``APP_ENV=test`` uses in-memory stores. Every other environment requires
MongoDB and S3 configuration and connects during startup. Connection errors
raise a fixed message that does not include the URI or cloud credentials.
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pymongo import AsyncMongoClient
from pymongo.errors import PyMongoError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.protected import router as protected_router
from app.api.users import router as users_router
from app.config import Settings, load_settings
from app.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.logging_config import configure_logging
from app.middleware import RequestContextMiddleware
from app.repositories.document_repository import DocumentRepository
from app.repositories.errors import StorageError
from app.repositories.in_memory_document_repository import InMemoryDocumentRepository
from app.repositories.in_memory_user_repository import InMemoryUserRepository
from app.repositories.mongo_document_repository import MongoDocumentRepository
from app.repositories.mongo_user_repository import MongoUserRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.storage.in_memory_object_storage import InMemoryObjectStorage
from app.storage.object_storage import ObjectStorage
from app.storage.s3_object_storage import S3ObjectStorage

logger = logging.getLogger("app.main")

_ALLOWED_METHODS = ["GET", "POST", "PATCH", "DELETE", "OPTIONS"]
_ALLOWED_HEADERS = ["Authorization", "Content-Type", "X-Request-ID"]


def create_app(
    settings: Settings | None = None,
    *,
    user_repository: UserRepository | None = None,
    document_repository: DocumentRepository | None = None,
    object_storage: ObjectStorage | None = None,
) -> FastAPI:
    """Create the API application for the supplied settings."""
    resolved = settings or load_settings()
    resolved.validate_runtime()
    configure_logging(resolved)
    user_repository, document_repository, object_storage = _select_stores(
        resolved,
        user_repository,
        document_repository,
        object_storage,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await _open_external_stores(app)
        try:
            await app.state.user_repository.ensure_indexes()
            await app.state.document_repository.ensure_indexes()
            await AuthService(app.state.user_repository, app.state.settings).ensure_bootstrap_admin()
            yield
        finally:
            client = getattr(app.state, "mongo_client", None)
            if client is not None:
                await client.close()

    docs_url = None if resolved.is_production else "/docs"
    openapi_url = None if resolved.is_production else "/openapi.json"
    app = FastAPI(
        title=resolved.app_name,
        version=resolved.app_version,
        summary="Document-based GenAI assistant API.",
        docs_url=docs_url,
        redoc_url=None,
        openapi_url=openapi_url,
        lifespan=lifespan,
    )
    app.state.settings = resolved
    app.state.mongo_client = None
    app.state.user_repository = user_repository
    app.state.document_repository = document_repository
    app.state.object_storage = object_storage

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origins,
        allow_credentials=False,
        allow_methods=_ALLOWED_METHODS,
        allow_headers=_ALLOWED_HEADERS,
    )
    app.add_middleware(RequestContextMiddleware)

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(documents_router)
    app.include_router(protected_router)
    app.add_exception_handler(AppError, app_error_handler)
    # FastAPI's HTTPException subclasses Starlette's. Routing 404s use the
    # Starlette class, so the handler has to be registered on that class.
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    return app


def _select_stores(
    settings: Settings,
    user_repository: UserRepository | None,
    document_repository: DocumentRepository | None,
    object_storage: ObjectStorage | None,
) -> tuple[UserRepository | None, DocumentRepository | None, ObjectStorage | None]:
    supplied = (user_repository is not None, document_repository is not None, object_storage is not None)
    if any(supplied) and not all(supplied):
        raise RuntimeError("Storage overrides must be provided together.")
    if all(supplied):
        return user_repository, document_repository, object_storage
    if settings.app_env == "test":
        return InMemoryUserRepository(), InMemoryDocumentRepository(), InMemoryObjectStorage()
    error = settings.storage_configuration_error()
    if error:
        raise RuntimeError(error)
    return None, None, None


async def _open_external_stores(app: FastAPI) -> None:
    """Connect to MongoDB and S3 when the factory left the stores empty."""
    if app.state.user_repository is not None:
        return
    settings: Settings = app.state.settings
    client: AsyncMongoClient = AsyncMongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
    try:
        await client.aconnect()
        storage = S3ObjectStorage.from_settings(settings)
        await asyncio.to_thread(storage.check)
    except (PyMongoError, OSError, StorageError):
        await client.close()
        logger.info("external store unavailable", extra={"exception_type": "connection_failed"})
        raise RuntimeError("MongoDB or object storage is unavailable.") from None
    database = client[settings.mongodb_database]
    app.state.mongo_client = client
    app.state.user_repository = MongoUserRepository(database["users"])
    app.state.document_repository = MongoDocumentRepository(database["documents"])
    app.state.object_storage = storage


app = create_app()
