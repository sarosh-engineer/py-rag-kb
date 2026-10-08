# GET /health

Liveness probe for the API process.

## Request

```http
GET /health HTTP/1.1
X-Request-ID: req-123
```

`X-Request-ID` is optional. When it is 1 to 128 characters from `[A-Za-z0-9._-]`, the same value is returned. Otherwise the server generates a new id.

## Response

`200 OK`

```json
{
  "status": "ok",
  "service": "genai-rag-assistant",
  "environment": "local",
  "version": "0.1.0"
}
```

The response includes `X-Request-ID`.

## What this does not mean

`status: ok` means this Python process handled the request. It does not mean S3, MongoDB Atlas, or Bedrock are reachable. Those checks are not part of Phase 1.

## Errors

| Status | Code | When |
| --- | --- | --- |
| 404 | `http_error` | Any unknown path, including a misspelled health path |
| 500 | `internal_error` | Unexpected failure while handling the request |

Error bodies use this shape:

```json
{
  "error": {
    "code": "http_error",
    "message": "Not Found",
    "request_id": "req-123"
  }
}
```
