"""Registration, login, and the current-user route."""

from fastapi import APIRouter

from app.config import Settings
from app.dependencies import SettingsDep
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.errors import error_responses
from app.schemas.user import UserPublic
from app.security.authorization import CurrentUserDep, UserRepositoryDep
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(settings: Settings, users: UserRepositoryDep) -> AuthService:
    return AuthService(users, settings)


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=201,
    responses=error_responses(409, 422, 503),
    summary="Register a viewer account",
)
async def register(
    body: RegisterRequest,
    settings: SettingsDep,
    users: UserRepositoryDep,
) -> UserPublic:
    """Create a viewer. The request body has no role field.

    A token is not returned. The client signs in with ``POST /auth/login``.
    """
    user = await get_auth_service(settings, users).register(body.email, body.password)
    return UserPublic.from_user(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    responses=error_responses(401, 422, 503),
    summary="Exchange credentials for an access token",
)
async def login(
    body: LoginRequest,
    settings: SettingsDep,
    users: UserRepositoryDep,
) -> TokenResponse:
    """Return a bearer token. Failures use one message for every credential error."""
    service = get_auth_service(settings, users)
    user = await service.authenticate(body.email, body.password)
    return TokenResponse(
        access_token=service.issue_token(user),
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserPublic.from_user(user),
    )


@router.get(
    "/me",
    response_model=UserPublic,
    responses=error_responses(401, 503),
    summary="Return the authenticated account",
)
def read_me(user: CurrentUserDep) -> UserPublic:
    """Return the account loaded from the repository for this token."""
    return UserPublic.from_user(user)
