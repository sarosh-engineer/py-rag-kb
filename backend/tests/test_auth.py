"""Registration, login, and the current-user route."""

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.models.user import Role
from tests.auth_helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    VIEWER_EMAIL,
    VIEWER_PASSWORD,
    bearer,
    login,
    register,
)


def test_register_creates_an_active_viewer(client: TestClient) -> None:
    body = register(client)

    assert body["email"] == VIEWER_EMAIL
    assert body["role"] == "viewer"
    assert body["is_active"] is True
    assert body["id"]
    assert "password" not in body
    assert "password_hash" not in body
    stored = client.app.state.user_repository.get_by_email(VIEWER_EMAIL)
    assert stored is not None
    assert stored.password_hash != VIEWER_PASSWORD
    assert stored.password_hash.startswith("$argon2")


def test_register_normalizes_email_and_rejects_duplicates(client: TestClient) -> None:
    register(client, email="Viewer@Example.com")

    duplicate = client.post(
        "/auth/register",
        json={"email": "viewer@example.com", "password": VIEWER_PASSWORD},
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "email_taken"


def test_register_rejects_a_role_field(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={"email": VIEWER_EMAIL, "password": VIEWER_PASSWORD, "role": "admin"},
    )

    assert response.status_code == 422
    assert client.app.state.user_repository.get_by_email(VIEWER_EMAIL) is None
    assert "password_hash" not in response.text


def test_register_rejects_a_short_password(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={"email": VIEWER_EMAIL, "password": "short-1"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "short-1" not in response.text


def test_register_rejects_an_invalid_email(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": VIEWER_PASSWORD},
    )

    assert response.status_code == 422


def test_login_returns_a_token_and_the_public_user(client: TestClient) -> None:
    register(client)

    body = login(client, VIEWER_EMAIL, VIEWER_PASSWORD)

    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 30 * 60
    assert body["user"]["role"] == "viewer"
    assert "password" not in body["user"]
    assert "$argon2" not in body["access_token"]
    me = client.get("/auth/me", headers=bearer(body["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == VIEWER_EMAIL


def test_login_uses_the_same_error_for_unknown_and_wrong_password(client: TestClient) -> None:
    register(client)
    wrong_password = client.post(
        "/auth/login",
        json={"email": VIEWER_EMAIL, "password": "wrong-password-1"},
    )
    unknown_user = client.post(
        "/auth/login",
        json={"email": "missing@example.com", "password": VIEWER_PASSWORD},
    )

    assert wrong_password.status_code == 401
    assert unknown_user.status_code == 401
    assert wrong_password.json()["error"]["code"] == "invalid_credentials"
    assert unknown_user.json()["error"]["code"] == wrong_password.json()["error"]["code"]
    assert unknown_user.json()["error"]["message"] == wrong_password.json()["error"]["message"]
    assert "viewer@example.com" not in unknown_user.text


def test_disabled_user_gets_the_same_login_error(client: TestClient) -> None:
    created = register(client)
    admin = _admin_token(client)
    disabled = client.patch(
        f"/users/{created['id']}",
        json={"is_active": False},
        headers=bearer(admin),
    )
    assert disabled.status_code == 200

    response = client.post(
        "/auth/login",
        json={"email": VIEWER_EMAIL, "password": VIEWER_PASSWORD},
    )
    wrong_password = client.post(
        "/auth/login",
        json={"email": VIEWER_EMAIL, "password": "wrong-password-1"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == wrong_password.json()["error"]["code"]
    assert response.json()["error"]["message"] == wrong_password.json()["error"]["message"]


def test_login_is_unavailable_without_a_signing_key() -> None:
    application = create_app(Settings(app_env="test", log_level="ERROR", jwt_secret_key=""))
    with TestClient(application) as client:
        assert client.get("/health").status_code == 200
        response = client.post(
            "/auth/login",
            json={"email": VIEWER_EMAIL, "password": VIEWER_PASSWORD},
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "auth_not_configured"


def test_bootstrap_admin_can_sign_in() -> None:
    application = create_app(
        Settings(
            app_env="test",
            log_level="ERROR",
            jwt_secret_key="y" * 32,
            bootstrap_admin_email=ADMIN_EMAIL,
            bootstrap_admin_password=ADMIN_PASSWORD,
        )
    )
    with TestClient(application) as client:
        body = login(client, ADMIN_EMAIL, ADMIN_PASSWORD)

    assert body["user"]["role"] == "admin"
    assert ADMIN_PASSWORD not in str(body)


def test_bootstrap_settings_must_be_paired() -> None:
    with pytest.raises(RuntimeError, match="both"):
        create_app(
            Settings(
                app_env="test",
                jwt_secret_key="y" * 32,
                bootstrap_admin_email=ADMIN_EMAIL,
            )
        )


def test_production_refuses_to_start_without_a_signing_key() -> None:
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        create_app(Settings(app_env="production", jwt_secret_key="too-short"))


def _admin_token(client: TestClient) -> str:
    """Create a second app user and promote them with a seeded admin token.

    The shared client has no bootstrap admin. Seed one through the repository
    only inside this helper, then promote the caller-created viewer.
    """
    from datetime import UTC, datetime
    from uuid import uuid4

    from app.models.user import User
    from app.security.password import hash_password

    repository = client.app.state.user_repository
    if repository.get_by_email(ADMIN_EMAIL) is None:
        repository.add(
            User(
                id=uuid4().hex,
                email=ADMIN_EMAIL,
                password_hash=hash_password(ADMIN_PASSWORD),
                role=Role.ADMIN,
                is_active=True,
                created_at=datetime.now(UTC),
            )
        )
    return login(client, ADMIN_EMAIL, ADMIN_PASSWORD)["access_token"]
