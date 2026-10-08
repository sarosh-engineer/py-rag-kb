# Document API

All routes require `Authorization: Bearer <access_token>`.

Allowed upload types are PDF, plain text, Markdown, and DOCX. The default size limit is 10 MiB (`MAX_UPLOAD_BYTES`).

## POST /documents

Multipart field name: `file`. Admin and editor. Viewer receives `403`.

```bash
curl -s -X POST http://127.0.0.1:8000/documents \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@notes.txt;type=text/plain"
```

The JSON body is document metadata. It has no S3 key and no credentials.

| Status | Code | When |
| --- | --- | --- |
| 201 | | Stored |
| 400 | `invalid_filename` or `empty_file` | Name or body rejected |
| 401 | `unauthorized` | Missing or invalid token |
| 403 | `forbidden` | Viewer |
| 413 | `file_too_large` | Over `MAX_UPLOAD_BYTES` |
| 415 | `unsupported_media_type` | Type not on the allowlist |
| 503 | `storage_unavailable` or `metadata_write_failed` | S3 or MongoDB failed |

## GET /documents

Any active account. Returns metadata for every document. Document-level filtering is a later phase.

## GET /documents/{document_id}/content

Any active account. Returns the file bytes and a `Content-Disposition` filename.

## DELETE /documents/{document_id}

Admin only. Editors and viewers receive `403`.

Success is `204` only when both the object and the metadata row are gone. A failure leaves the row, often with status `delete_pending`, and returns `503`.
