"""FastAPI dependencies shared by route modules.

Routes depend on functions defined here so tests can override them and so
authorization checks, added in a later phase, have one obvious home.
"""

from typing import Annotated

from fastapi import Depends, Request

from app.config import Settings


def get_settings(request: Request) -> Settings:
    """Return the settings bound to this application instance."""
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        raise RuntimeError("Application settings are not initialized")
    return settings


SettingsDep = Annotated[Settings, Depends(get_settings)]
