"""Shared authentication fixtures for API tests."""

from fastapi.testclient import TestClient

from app.models.user import Role

TEST_JWT_SECRET = "x" * 32
VIEWER_EMAIL = "viewer@example.com"
VIEWER_PASSWORD = "viewer-password-1"
EDITOR_EMAIL = "editor@example.com"
EDITOR_PASSWORD = "editor-password-1"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin-password-1"


def register(client: TestClient, email: str = VIEWER_EMAIL, password: str = VIEWER_PASSWORD) -> dict:
    response = client.post("/auth/register", json={"email": email, "password": password})
    assert response.status_code == 201, response.text
    return response.json()


def login(client: TestClient, email: str, password: str) -> dict:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def promote(client: TestClient, user_id: str, role: Role, admin_token: str) -> None:
    response = client.patch(
        f"/users/{user_id}",
        json={"role": role.value},
        headers=bearer(admin_token),
    )
    assert response.status_code == 200, response.text
