"""Shared fixtures.

Each test gets its own application instance. The module-level ``app`` in
``app.main`` is only the object Uvicorn imports.
"""

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_env="test",
        log_level="WARNING",
        log_json=True,
        cors_allowed_origins="",
    )


@pytest.fixture
def client(settings: Settings) -> TestClient:
    application = create_app(settings)
    with TestClient(application) as test_client:
        yield test_client
