"""Document metadata stored beside the S3 object.

``s3_key`` stays on this model and out of API responses. Owner, allowed
roles, allowed users, and tenant id are stored now so a later phase can
filter retrieval without a migration that invents those fields from scratch.
This phase does not enforce those grants.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import Role


class DocumentStatus(StrEnum):
    """Lifecycle of one stored file."""

    UPLOADED = "uploaded"
    DELETE_PENDING = "delete_pending"


class Document(BaseModel):
    """One uploaded file and the fields needed for later authorization."""

    model_config = ConfigDict(frozen=True)

    id: str
    original_filename: str
    s3_key: str
    content_type: str
    size_bytes: int
    uploaded_by: str
    owner_id: str
    allowed_roles: list[Role] = Field(default_factory=list)
    allowed_user_ids: list[str] = Field(default_factory=list)
    tenant_id: str | None = None
    status: DocumentStatus = DocumentStatus.UPLOADED
    created_at: datetime
    updated_at: datetime
