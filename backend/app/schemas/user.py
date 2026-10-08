"""Public user representations. Password hashes never appear here."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import Role, User


class UserPublic(BaseModel):
    """Account fields a client is allowed to see."""

    id: str
    email: str
    role: Role
    is_active: bool
    created_at: datetime

    @classmethod
    def from_user(cls, user: User) -> "UserPublic":
        return cls(
            id=user.id,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
        )


class UserUpdate(BaseModel):
    """Admin change to a role, an active flag, or both."""

    model_config = ConfigDict(extra="forbid")

    role: Role | None = None
    is_active: bool | None = Field(default=None)

    def changed(self) -> bool:
        return self.role is not None or self.is_active is not None
