"""Backend role checks. These requests bypass any future user interface."""

import asyncio

from fastapi.testclient import TestClient

from app.models.user import Role
from tests.auth_helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    EDITOR_EMAIL,
    EDITOR_PASSWORD,
    VIEWER_EMAIL,
    VIEWER_PASSWORD,
    bearer,
    login,
    promote,
    register,
)


def test_missing_token_is_rejected(client: TestClient) -> None:
    response = client.get("/protected/user")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
    assert response.headers["www-authenticate"] == "Bearer"


def test_role_matrix(client: TestClient) -> None:
    tokens = _tokens(client)
    expectations = {
        "viewer": {"/protected/user": 200, "/protected/editor": 403, "/protected/admin": 403},
        "editor": {"/protected/user": 200, "/protected/editor": 200, "/protected/admin": 403},
        "admin": {"/protected/user": 200, "/protected/editor": 200, "/protected/admin": 200},
    }

    for role, paths in expectations.items():
        for path, status in paths.items():
            response = client.get(path, headers=bearer(tokens[role]))
            assert response.status_code == status, f"{role} {path} -> {response.status_code} {response.text}"
            if status == 403:
                assert response.json()["error"]["code"] == "forbidden"


def test_viewer_cannot_manage_users(client: TestClient) -> None:
    created = register(client)
    token = login(client, VIEWER_EMAIL, VIEWER_PASSWORD)["access_token"]

    listing = client.get("/users", headers=bearer(token))
    change = client.patch(
        f"/users/{created['id']}",
        json={"role": "admin"},
        headers=bearer(token),
    )

    assert listing.status_code == 403
    assert change.status_code == 403
    stored = asyncio.run(client.app.state.user_repository.get_by_email(VIEWER_EMAIL))
    assert stored.role is Role.VIEWER


def test_editor_cannot_manage_users(client: TestClient) -> None:
    tokens = _tokens(client)
    editor = asyncio.run(client.app.state.user_repository.get_by_email(EDITOR_EMAIL))

    listing = client.get("/users", headers=bearer(tokens["editor"]))
    change = client.patch(
        f"/users/{editor.id}",
        json={"role": "admin"},
        headers=bearer(tokens["editor"]),
    )

    assert listing.status_code == 403
    assert change.status_code == 403
    assert editor.role is Role.EDITOR


def test_admin_can_change_another_users_role(client: TestClient) -> None:
    tokens = _tokens(client)
    viewer = asyncio.run(client.app.state.user_repository.get_by_email(VIEWER_EMAIL))

    response = client.patch(
        f"/users/{viewer.id}",
        json={"role": "editor"},
        headers=bearer(tokens["admin"]),
    )

    assert response.status_code == 200
    assert response.json()["role"] == "editor"
    assert "password_hash" not in response.text
    assert "$argon2" not in response.text
    me = client.get("/auth/me", headers=bearer(tokens["viewer"]))
    assert me.status_code == 200
    assert me.json()["role"] == "editor"


def test_admin_cannot_remove_their_own_access(client: TestClient) -> None:
    tokens = _tokens(client)
    admin = asyncio.run(client.app.state.user_repository.get_by_email(ADMIN_EMAIL))

    demote = client.patch(
        f"/users/{admin.id}",
        json={"role": "viewer"},
        headers=bearer(tokens["admin"]),
    )
    disable = client.patch(
        f"/users/{admin.id}",
        json={"is_active": False},
        headers=bearer(tokens["admin"]),
    )

    assert demote.status_code == 400
    assert demote.json()["error"]["code"] == "cannot_change_self"
    assert disable.status_code == 400
    assert asyncio.run(client.app.state.user_repository.get_by_id(admin.id)).role is Role.ADMIN


def test_disabled_token_stops_working(client: TestClient) -> None:
    tokens = _tokens(client)
    viewer = asyncio.run(client.app.state.user_repository.get_by_email(VIEWER_EMAIL))

    disabled = client.patch(
        f"/users/{viewer.id}",
        json={"is_active": False},
        headers=bearer(tokens["admin"]),
    )
    me = client.get("/auth/me", headers=bearer(tokens["viewer"]))

    assert disabled.status_code == 200
    assert me.status_code == 401
    assert me.json()["error"]["code"] == "unauthorized"


def test_user_list_omits_secrets(client: TestClient) -> None:
    tokens = _tokens(client)

    response = client.get("/users", headers=bearer(tokens["admin"]))

    assert response.status_code == 200
    assert len(response.json()) == 3
    assert "$argon2" not in response.text
    assert "password" not in response.text


def _tokens(client: TestClient) -> dict[str, str]:
    register(client, VIEWER_EMAIL, VIEWER_PASSWORD)
    editor = register(client, EDITOR_EMAIL, EDITOR_PASSWORD)
    admin = register(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    # Public registration cannot create an admin. Tests seed that one row
    # through the repository, which is the same boundary a migration would use.
    stored_admin = asyncio.run(client.app.state.user_repository.get_by_id(admin["id"]))
    asyncio.run(
        client.app.state.user_repository.update(stored_admin.model_copy(update={"role": Role.ADMIN}))
    )
    admin_token = login(client, ADMIN_EMAIL, ADMIN_PASSWORD)["access_token"]
    promote(client, editor["id"], Role.EDITOR, admin_token)
    return {
        "viewer": login(client, VIEWER_EMAIL, VIEWER_PASSWORD)["access_token"],
        "editor": login(client, EDITOR_EMAIL, EDITOR_PASSWORD)["access_token"],
        "admin": admin_token,
    }
