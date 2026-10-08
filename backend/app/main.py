"""FastAPI application factory.

``create_app`` builds a fully configured application. The module-level
``app`` object is what ``uvicorn app.main:app`` serves. Tests call
``create_app`` with an explicit ``Settings`` instance so they do not depend
on the developer machine's environment.
"""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.health import router as health_router
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

# Methods and headers the browser is allowed to send. Phase 1 only serves
# GET /health. Later phases must extend these lists when they add routes.
_ALLOWED_METHODS = ["GET", "OPTIONS"]
_ALLOWED_HEADERS = ["Content-Type", "X-Request-ID"]


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the API application for the supplied settings."""
    resolved = settings or load_settings()
    configure_logging(resolved)

    docs_url = None if resolved.is_production else "/docs"
    openapi_url = None if resolved.is_production else "/openapi.json"

    app = FastAPI(
        title=resolved.app_name,
        version=resolved.app_version,
        summary="Document-based GenAI assistant API.",
        docs_url=docs_url,
        redoc_url=None,
        openapi_url=openapi_url,
    )
    app.state.settings = resolved

    # Added last so it is the outermost middleware and sees every response.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origins,
        allow_credentials=False,
        allow_methods=_ALLOWED_METHODS,
        allow_headers=_ALLOWED_HEADERS,
    )
    app.add_middleware(RequestContextMiddleware)

    app.include_router(health_router)
    app.add_exception_handler(AppError, app_error_handler)
    # FastAPI's HTTPException subclasses Starlette's. Routing 404s use the
    # Starlette class, so the handler has to be registered on that class.
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    return app


app = create_app()
