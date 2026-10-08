"""FastAPI dependencies shared by route modules.

Settings stay here. Authentication and role checks live in
``app.security.authorization`` so token parsing is not mixed with generic
application wiring.
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
