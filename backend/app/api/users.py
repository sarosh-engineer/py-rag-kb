"""Admin account management."""

from fastapi import APIRouter

from app.dependencies import SettingsDep
from app.errors import AppError
from app.schemas.errors import error_responses
from app.schemas.user import UserPublic, UserUpdate
from app.security.authorization import AdminDep, UserRepositoryDep
from app.services.auth_service import AuthService

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "",
    response_model=list[UserPublic],
    responses=error_responses(401, 403),
    summary="List accounts",
)
async def list_users(_actor: AdminDep, users: UserRepositoryDep) -> list[UserPublic]:
    """Return every account. Admin only. Password hashes are not included."""
    return [UserPublic.from_user(user) for user in await users.list_users()]


@router.patch(
    "/{user_id}",
    response_model=UserPublic,
    responses=error_responses(400, 401, 403, 404, 422),
    summary="Change a role or active flag",
)
async def update_user(
    user_id: str,
    body: UserUpdate,
    actor: AdminDep,
    settings: SettingsDep,
    users: UserRepositoryDep,
) -> UserPublic:
    """Assign a role or enable or disable an account. Admin only."""
    if not body.changed():
        raise AppError(
            "Provide a role, an active flag, or both.",
            status_code=422,
            code="validation_error",
        )
    updated = await AuthService(users, settings).update_user(
        actor,
        user_id,
        role=body.role,
        is_active=body.is_active,
    )
    return UserPublic.from_user(updated)
