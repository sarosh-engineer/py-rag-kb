"""Document upload, listing, download, and delete.

Role checks are dependencies. This module does not call MongoDB or boto3.
"""

from fastapi import APIRouter, UploadFile
from fastapi.responses import Response

from app.dependencies import DocumentRepositoryDep, ObjectStorageDep, SettingsDep
from app.schemas.document import DocumentPublic
from app.schemas.errors import error_responses
from app.security.authorization import AdminDep, CurrentUserDep, EditorDep
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


def _service(
    documents: DocumentRepositoryDep,
    storage: ObjectStorageDep,
    settings: SettingsDep,
) -> DocumentService:
    return DocumentService(documents, storage, settings)


@router.post(
    "",
    response_model=DocumentPublic,
    status_code=201,
    responses=error_responses(400, 401, 403, 413, 415, 503),
    summary="Upload a document",
)
async def upload_document(
    file: UploadFile,
    user: EditorDep,
    documents: DocumentRepositoryDep,
    storage: ObjectStorageDep,
    settings: SettingsDep,
) -> DocumentPublic:
    """Store a file. Admin and editor only. Viewers receive 403."""
    document = await _service(documents, storage, settings).upload(user, file)
    return DocumentPublic.from_document(document)


@router.get(
    "",
    response_model=list[DocumentPublic],
    responses=error_responses(401, 503),
    summary="List document metadata",
)
async def list_documents(
    _user: CurrentUserDep,
    documents: DocumentRepositoryDep,
    storage: ObjectStorageDep,
    settings: SettingsDep,
) -> list[DocumentPublic]:
    """Return metadata for every document. Any active account may list."""
    rows = await _service(documents, storage, settings).list_documents()
    return [DocumentPublic.from_document(row) for row in rows]


@router.get(
    "/{document_id}/content",
    responses=error_responses(401, 404, 503),
    summary="Download a document",
)
async def download_document(
    document_id: str,
    _user: CurrentUserDep,
    documents: DocumentRepositoryDep,
    storage: ObjectStorageDep,
    settings: SettingsDep,
) -> Response:
    """Return the file bytes. The client does not receive storage credentials."""
    document, body = await _service(documents, storage, settings).read_content(document_id)
    return Response(
        content=body,
        media_type=document.content_type,
        headers={"Content-Disposition": f'attachment; filename="{document.original_filename}"'},
    )


@router.delete(
    "/{document_id}",
    status_code=204,
    responses=error_responses(401, 403, 404, 503),
    summary="Delete a document",
)
async def delete_document(
    document_id: str,
    _user: AdminDep,
    documents: DocumentRepositoryDep,
    storage: ObjectStorageDep,
    settings: SettingsDep,
) -> Response:
    """Delete the object and its metadata. Admin only. Editors receive 403."""
    await _service(documents, storage, settings).delete(document_id)
    return Response(status_code=204)
