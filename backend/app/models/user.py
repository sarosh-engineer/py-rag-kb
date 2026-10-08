"""User identity used by authentication.

The shape is storage-neutral. ``id`` is a string so a later MongoDB
repository can persist the same value without changing the API.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Role(StrEnum):
    """Application roles. Compare these members, not raw strings."""

    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class User(BaseModel):
    """Persisted account, including the password hash.

    API schemas must not reuse this model. Routes return ``UserPublic``.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    email: str
    password_hash: str
    role: Role
    is_active: bool = True
    created_at: datetime = Field(description="UTC timestamp.")
