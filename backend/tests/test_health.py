"""Health endpoint and request context."""

import logging

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_health_reports_configured_identity(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "genai-rag-assistant",
        "environment": "test",
        "version": "0.1.0",
    }


def test_health_echoes_a_safe_request_id(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "req-123"})

    assert response.headers["x-request-id"] == "req-123"


def test_unsafe_request_id_is_replaced(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "bad id\ninjected"})

    request_id = response.headers["x-request-id"]
    assert request_id != "bad id\ninjected"
    assert "\n" not in request_id
    assert response.json()["status"] == "ok"


def test_access_log_records_path_status_and_duration(caplog: pytest.LogCaptureFixture) -> None:
    application = create_app(Settings(app_env="test", log_level="INFO", log_json=True))
    caplog.set_level(logging.INFO, logger="app.access")

    with TestClient(application) as test_client:
        response = test_client.get("/health", headers={"X-Request-ID": "req-health"})

    records = [record for record in caplog.records if record.name == "app.access"]
    assert len(records) == 1
    record = records[0]
    assert record.request_id == "req-health"
    assert record.method == "GET"
    assert record.path == "/health"
    assert record.status_code == 200
    assert record.duration_ms >= 0
    assert response.headers["x-request-id"] == "req-health"


def test_configured_origin_is_allowed() -> None:
    application = create_app(
        Settings(
            app_env="test",
            log_level="WARNING",
            cors_allowed_origins="http://localhost:4200",
        )
    )

    with TestClient(application) as test_client:
        response = test_client.get("/health", headers={"Origin": "http://localhost:4200"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:4200"


def test_unlisted_origin_is_not_reflected(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": "http://evil.example"})

    assert "access-control-allow-origin" not in response.headers


def test_openapi_is_hidden_in_production() -> None:
    from app.repositories.in_memory_document_repository import InMemoryDocumentRepository
    from app.repositories.in_memory_user_repository import InMemoryUserRepository
    from app.storage.in_memory_object_storage import InMemoryObjectStorage

    application = create_app(
        Settings(app_env="production", log_level="WARNING", jwt_secret_key="p" * 32),
        user_repository=InMemoryUserRepository(),
        document_repository=InMemoryDocumentRepository(),
        object_storage=InMemoryObjectStorage(),
    )

    with TestClient(application) as test_client:
        assert test_client.get("/docs").status_code == 404
        assert test_client.get("/openapi.json").status_code == 404


def test_openapi_is_available_outside_production(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/health" in response.json()["paths"]
