"""Client-facing errors stay explicit and do not leak internals."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.config import Settings
from app.errors import AppError
from app.main import create_app


class _Item(BaseModel):
    name: str


def _client_with_probes(settings: Settings | None = None) -> tuple[FastAPI, TestClient]:
    application = create_app(settings or Settings(app_env="test", log_level="ERROR"))

    @application.get("/probe/boom")
    def boom() -> dict[str, str]:
        raise RuntimeError("password=supersecret")

    @application.get("/probe/expected")
    def expected() -> dict[str, str]:
        raise AppError("The document was not found.", status_code=404, code="not_found")

    @application.post("/probe/items")
    def create_item(item: _Item) -> dict[str, str]:
        return item.model_dump()

    return application, TestClient(application, raise_server_exceptions=False)


def test_unknown_route_uses_the_public_error_shape(client: TestClient) -> None:
    response = client.get("/missing")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "http_error"
    assert body["error"]["message"] == "Not Found"
    assert body["error"]["request_id"] == response.headers["x-request-id"]
    assert "traceback" not in response.text.lower()


def test_validation_errors_omit_submitted_values() -> None:
    _, test_client = _client_with_probes()

    response = test_client.post(
        "/probe/items",
        json={"name": 1, "password": "supersecret"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["details"]
    assert "supersecret" not in response.text
    assert "input" not in body["error"]


def test_expected_application_errors_keep_their_safe_message() -> None:
    _, test_client = _client_with_probes()

    response = test_client.get("/probe/expected")

    assert response.status_code == 404
    assert response.json()["error"] == {
        "code": "not_found",
        "message": "The document was not found.",
        "request_id": response.headers["x-request-id"],
    }


def test_unexpected_errors_hide_the_exception_and_keep_cors() -> None:
    settings = Settings(
        app_env="test",
        log_level="ERROR",
        cors_allowed_origins="http://localhost:4200",
    )
    _, test_client = _client_with_probes(settings)

    response = test_client.get("/probe/boom", headers={"Origin": "http://localhost:4200"})

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["message"] == "An unexpected error occurred."
    assert "supersecret" not in response.text
    assert "Traceback" not in response.text
    assert response.headers["x-request-id"] == body["error"]["request_id"]
    assert response.headers["access-control-allow-origin"] == "http://localhost:4200"
