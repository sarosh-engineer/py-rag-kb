"""Demonstration routes for role checks.

These endpoints exist so tests and Swagger can show RBAC. They are not
product features. Remove them when document and chat routes cover the same
permissions.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.models.user import Role
from app.schemas.errors import error_responses
from app.security.authorization import AdminDep, CurrentUserDep, EditorDep

router = APIRouter(prefix="/protected", tags=["rbac-demo"])


class ProtectedAccess(BaseModel):
    """Which demonstration route accepted the caller."""

    access: str
    role: Role


@router.get(
    "/user",
    response_model=ProtectedAccess,
    responses=error_responses(401),
    summary="Any authenticated role",
)
def authenticated_probe(user: CurrentUserDep) -> ProtectedAccess:
    """Allow admin, editor, and viewer."""
    return ProtectedAccess(access="authenticated", role=user.role)


@router.get(
    "/editor",
    response_model=ProtectedAccess,
    responses=error_responses(401, 403),
    summary="Editor or admin",
)
def editor_probe(user: EditorDep) -> ProtectedAccess:
    """Allow editor and admin. Viewer is forbidden."""
    return ProtectedAccess(access="editor", role=user.role)


@router.get(
    "/admin",
    response_model=ProtectedAccess,
    responses=error_responses(401, 403),
    summary="Admin only",
)
def admin_probe(user: AdminDep) -> ProtectedAccess:
    """Allow admin only."""
    return ProtectedAccess(access="admin", role=user.role)
