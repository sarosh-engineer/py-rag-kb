"""Upload validation. Limits live in settings. Types are an explicit allowlist."""

from fastapi import UploadFile

from app.config import Settings
from app.errors import AppError

ALLOWED_CONTENT_TYPES: dict[str, set[str]] = {
    "application/pdf": {".pdf"},
    "text/plain": {".txt"},
    "text/markdown": {".md", ".markdown"},
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {".docx"},
}


async def read_upload(upload: UploadFile, settings: Settings, safe_filename: str) -> bytes:
    """Read the body after checking type and size."""
    content_type = (upload.content_type or "").split(";", 1)[0].strip().lower()
    extensions = ALLOWED_CONTENT_TYPES.get(content_type)
    suffix = _suffix(safe_filename)
    if extensions is None or suffix not in extensions:
        raise AppError(
            "This file type is not allowed.",
            status_code=415,
            code="unsupported_media_type",
        )
    chunks: list[bytes] = []
    total = 0
    while True:
        block = await upload.read(1024 * 1024)
        if not block:
            break
        total += len(block)
        if total > settings.max_upload_bytes:
            raise AppError("The file is too large.", status_code=413, code="file_too_large")
        chunks.append(block)
    if total == 0:
        raise AppError("The file is empty.", status_code=400, code="empty_file")
    return b"".join(chunks)


def _suffix(filename: str) -> str:
    if "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()
