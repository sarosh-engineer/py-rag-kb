"""Public document metadata. The S3 key and bucket are omitted."""

from datetime import datetime

from pydantic import BaseModel

from app.models.document import Document, DocumentStatus
from app.models.user import Role


class DocumentPublic(BaseModel):
    """Fields a client may see after upload or listing."""

    id: str
    original_filename: str
    content_type: str
    size_bytes: int
    uploaded_by: str
    owner_id: str
    allowed_roles: list[Role]
    allowed_user_ids: list[str]
    tenant_id: str | None
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_document(cls, document: Document) -> "DocumentPublic":
        return cls(
            id=document.id,
            original_filename=document.original_filename,
            content_type=document.content_type,
            size_bytes=document.size_bytes,
            uploaded_by=document.uploaded_by,
            owner_id=document.owner_id,
            allowed_roles=list(document.allowed_roles),
            allowed_user_ids=list(document.allowed_user_ids),
            tenant_id=document.tenant_id,
            status=document.status,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )
