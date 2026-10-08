"""Liveness route used by humans, tests, and container probes."""

from fastapi import APIRouter

from app.dependencies import SettingsDep
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def read_health(settings: SettingsDep) -> HealthResponse:
    """Report that this process is running.

    The handler is synchronous because it does no I/O. Async endpoints are
    reserved for calls that would otherwise block the event loop.
    """
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.app_env,
        version=settings.app_version,
    )
