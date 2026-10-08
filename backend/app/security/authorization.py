"""Authentication and role dependencies.

Protect a route by declaring one of these dependencies. The check runs on
the server for every request. Hiding a control in Angular does not replace it.

``require_roles`` is an explicit allow-list. Admin access is not implied.
A route that editors and admins may call must list both roles.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.dependencies import SettingsDep
from app.errors import AppError
from app.models.user import Role, User
from app.repositories.errors import RepositoryUnavailable
from app.repositories.user_repository import UserRepository
from app.security.jwt import authentication_required, read_access_token

bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Access token returned by POST /auth/login.",
)


def get_user_repository(request: Request) -> UserRepository:
    """Return the user store bound to this application."""
    repository = getattr(request.app.state, "user_repository", None)
    if not isinstance(repository, UserRepository):
        raise RuntimeError("User repository is not initialized")
    return repository


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    settings: SettingsDep,
    users: UserRepositoryDep,
) -> User:
    """Load the active user identified by the bearer token.

    The repository role is authoritative. A role claim left over from before
    an admin change does not grant the old permission. The extra indexed read
    is the cost of making disablement and demotion take effect immediately.
    Trusting the claim alone would skip the database and leave a disabled
    account active until the token expired.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise authentication_required()
    user_id, _role_claim = read_access_token(credentials.credentials, settings)
    try:
        user = await users.get_by_id(user_id)
    except RepositoryUnavailable:
        raise AppError(
            "The account store is unavailable.",
            status_code=503,
            code="store_unavailable",
        ) from None
    if user is None or not user.is_active:
        raise authentication_required()
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed: Role) -> Callable[[User], User]:
    """Build a dependency that allows only the listed roles."""
    if not allowed:
        raise ValueError("require_roles() needs at least one role")
    allowed_roles = frozenset(allowed)

    def dependency(user: CurrentUserDep) -> User:
        if user.role not in allowed_roles:
            raise AppError(
                "You do not have permission to perform this action.",
                status_code=403,
                code="forbidden",
            )
        return user

    return dependency


AdminDep = Annotated[User, Depends(require_roles(Role.ADMIN))]
EditorDep = Annotated[User, Depends(require_roles(Role.ADMIN, Role.EDITOR))]
