"""Document routes using the in-memory stores from the test application."""

import asyncio

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.models.user import Role
from app.repositories.errors import RepositoryUnavailable
from tests.auth_helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    EDITOR_EMAIL,
    EDITOR_PASSWORD,
    TEST_JWT_SECRET,
    VIEWER_EMAIL,
    VIEWER_PASSWORD,
    bearer,
    login,
    promote,
    register,
)


def test_unauthenticated_upload_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/documents",
        files={"file": ("notes.txt", b"hello document", "text/plain")},
    )

    assert response.status_code == 401


def test_viewer_cannot_upload_and_editor_and_admin_can(client: TestClient) -> None:
    tokens = _tokens(client)

    viewer = _upload(client, tokens["viewer"])
    editor = _upload(client, tokens["editor"], b"editor notes")
    admin = _upload(client, tokens["admin"], b"admin notes")

    assert viewer.status_code == 403
    assert editor.status_code == 201
    assert admin.status_code == 201
    assert editor.json()["original_filename"] == "notes.txt"
    assert "s3_key" not in editor.text
    assert "aws_secret" not in editor.text.lower()


def test_path_traversal_filename_is_stored_under_the_document_id(client: TestClient) -> None:
    tokens = _tokens(client)
    response = client.post(
        "/documents",
        files={"file": ("../../secret.txt", b"hello document", "text/plain")},
        headers=bearer(tokens["editor"]),
    )

    assert response.status_code == 201
    body = response.json()
    assert ".." not in body["original_filename"]
    stored = asyncio.run(client.app.state.document_repository.get(body["id"]))
    assert stored.s3_key.startswith(f"documents/{body['id']}/")
    assert ".." not in stored.s3_key


def test_invalid_type_and_oversize_file_are_rejected(client: TestClient) -> None:
    tokens = _tokens(client)
    invalid = client.post(
        "/documents",
        files={"file": ("pic.png", b"not-an-image", "image/png")},
        headers=bearer(tokens["editor"]),
    )
    assert invalid.status_code == 415

    small = create_app(
        Settings(
            app_env="test",
            log_level="ERROR",
            jwt_secret_key=TEST_JWT_SECRET,
            max_upload_bytes=8,
        )
    )
    with TestClient(small) as limited:
        _seed_editor(limited)
        token = login(limited, EDITOR_EMAIL, EDITOR_PASSWORD)["access_token"]
        oversized = limited.post(
            "/documents",
            files={"file": ("notes.txt", b"0123456789", "text/plain")},
            headers=bearer(token),
        )
    assert oversized.status_code == 413


def test_list_and_download_omit_storage_details(client: TestClient) -> None:
    tokens = _tokens(client)
    uploaded = _upload(client, tokens["editor"], b"hello document")
    document_id = uploaded.json()["id"]

    listing = client.get("/documents", headers=bearer(tokens["viewer"]))
    content = client.get(f"/documents/{document_id}/content", headers=bearer(tokens["viewer"]))

    assert listing.status_code == 200
    assert listing.json()[0]["id"] == document_id
    assert "s3_key" not in listing.text
    assert content.status_code == 200
    assert content.content == b"hello document"
    assert "secret" not in content.headers.get("content-disposition", "")


def test_only_admin_can_delete(client: TestClient) -> None:
    tokens = _tokens(client)
    document_id = _upload(client, tokens["editor"]).json()["id"]

    viewer = client.delete(f"/documents/{document_id}", headers=bearer(tokens["viewer"]))
    editor = client.delete(f"/documents/{document_id}", headers=bearer(tokens["editor"]))
    admin = client.delete(f"/documents/{document_id}", headers=bearer(tokens["admin"]))
    missing = client.get(f"/documents/{document_id}/content", headers=bearer(tokens["admin"]))

    assert viewer.status_code == 403
    assert editor.status_code == 403
    assert admin.status_code == 204
    assert missing.status_code == 404


def test_delete_reports_failure_when_object_storage_fails(client: TestClient) -> None:
    tokens = _tokens(client)
    document_id = _upload(client, tokens["admin"]).json()["id"]
    client.app.state.object_storage.fail_delete = True

    failed = client.delete(f"/documents/{document_id}", headers=bearer(tokens["admin"]))
    listing = client.get("/documents", headers=bearer(tokens["admin"]))

    assert failed.status_code == 503
    assert failed.json()["error"]["code"] == "storage_unavailable"
    assert listing.json()[0]["status"] == "delete_pending"


def test_delete_reports_failure_when_metadata_delete_fails(client: TestClient) -> None:
    tokens = _tokens(client)
    document_id = _upload(client, tokens["admin"]).json()["id"]

    async def fail_delete(ignored: str) -> None:
        del ignored
        raise RepositoryUnavailable

    client.app.state.document_repository.delete = fail_delete
    failed = client.delete(f"/documents/{document_id}", headers=bearer(tokens["admin"]))

    assert failed.status_code == 503
    assert failed.json()["error"]["code"] == "metadata_delete_failed"
    assert asyncio.run(client.app.state.document_repository.get(document_id)) is not None


def _upload(client: TestClient, token: str, payload: bytes = b"hello document"):
    return client.post(
        "/documents",
        files={"file": ("notes.txt", payload, "text/plain")},
        headers=bearer(token),
    )


def _tokens(client: TestClient) -> dict[str, str]:
    register(client, VIEWER_EMAIL, VIEWER_PASSWORD)
    _seed_editor(client)
    register(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    admin = asyncio.run(client.app.state.user_repository.get_by_email(ADMIN_EMAIL))
    asyncio.run(client.app.state.user_repository.update(admin.model_copy(update={"role": Role.ADMIN})))
    admin_token = login(client, ADMIN_EMAIL, ADMIN_PASSWORD)["access_token"]
    editor = asyncio.run(client.app.state.user_repository.get_by_email(EDITOR_EMAIL))
    promote(client, editor.id, Role.EDITOR, admin_token)
    return {
        "viewer": login(client, VIEWER_EMAIL, VIEWER_PASSWORD)["access_token"],
        "editor": login(client, EDITOR_EMAIL, EDITOR_PASSWORD)["access_token"],
        "admin": admin_token,
    }


def _seed_editor(client: TestClient) -> None:
    register(client, EDITOR_EMAIL, EDITOR_PASSWORD)
    editor = asyncio.run(client.app.state.user_repository.get_by_email(EDITOR_EMAIL))
    asyncio.run(client.app.state.user_repository.update(editor.model_copy(update={"role": Role.EDITOR})))
