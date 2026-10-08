"""Token contents, token failures, and log hygiene."""

import json
import logging
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.security.password import hash_password, verify_password
from tests.auth_helpers import TEST_JWT_SECRET, VIEWER_EMAIL, VIEWER_PASSWORD, bearer, login, register


def test_access_token_contains_only_the_minimum_claims(client: TestClient) -> None:
    register(client)
    token = login(client, VIEWER_EMAIL, VIEWER_PASSWORD)["access_token"]

    payload = jwt.decode(token, TEST_JWT_SECRET, algorithms=["HS256"])

    assert set(payload) == {"sub", "role", "typ", "iat", "exp"}
    assert payload["typ"] == "access"
    assert payload["role"] == "viewer"
    assert VIEWER_PASSWORD not in json.dumps(payload)
    assert "password" not in payload


def test_expired_and_invalid_tokens_are_rejected(client: TestClient) -> None:
    created = register(client)
    now = datetime.now(UTC)
    expired = jwt.encode(
        {
            "sub": created["id"],
            "role": "viewer",
            "typ": "access",
            "iat": int(now.timestamp()) - 120,
            "exp": int(now.timestamp()) - 30,
        },
        TEST_JWT_SECRET,
        algorithm="HS256",
    )
    wrong_key = jwt.encode(
        {
            "sub": created["id"],
            "role": "viewer",
            "typ": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
        },
        "z" * 32,
        algorithm="HS256",
    )
    bad_role = jwt.encode(
        {
            "sub": created["id"],
            "role": "owner",
            "typ": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
        },
        TEST_JWT_SECRET,
        algorithm="HS256",
    )

    for token in (expired, wrong_key, bad_role, "not-a-token"):
        response = client.get("/auth/me", headers=bearer(token))
        assert response.status_code == 401, response.text
        assert response.json()["error"]["code"] == "unauthorized"
        assert response.json()["error"]["message"] == "Authentication is required."
        assert VIEWER_PASSWORD not in response.text


def test_login_failure_does_not_log_the_password(caplog: pytest.LogCaptureFixture) -> None:
    application = create_app(
        Settings(app_env="test", log_level="INFO", jwt_secret_key=TEST_JWT_SECRET)
    )
    caplog.set_level(logging.INFO)
    password = "not-the-stored-password-1"
    with TestClient(application) as client:
        register(client)
        response = client.post("/auth/login", json={"email": VIEWER_EMAIL, "password": password})

    assert response.status_code == 401
    assert password not in caplog.text


def test_password_hash_verifies_and_does_not_store_plaintext() -> None:
    password = "correct-horse-1"
    stored = hash_password(password)

    assert stored != password
    assert verify_password(password, stored)
    assert verify_password("wrong-horse-1", stored) is False
    assert verify_password(password, "not-a-hash") is False


def test_openapi_documents_bearer_auth(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    schemes = schema["components"]["securitySchemes"]
    me = schema["paths"]["/auth/me"]["get"]

    assert any(item.get("scheme") == "bearer" and item.get("type") == "http" for item in schemes.values())
    assert me["security"]
    assert "Authentication is required." not in json.dumps(me["responses"].get("200", {}))
