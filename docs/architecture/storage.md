# MongoDB and S3

```text
FastAPI route
    |
    v
Service  (AuthService, DocumentService)
    |
    +--> UserRepository / DocumentRepository
    |         |
    |         +--> MongoUserRepository / MongoDocumentRepository
    |         |
    |         +--> in-memory doubles when APP_ENV=test
    |
    +--> ObjectStorage
              |
              +--> S3ObjectStorage
              |
              +--> in-memory double when APP_ENV=test
```

Routes do not import PyMongo or boto3. The service depends on the repository and storage protocols. `create_app` chooses the implementation. Tests pass the in-memory implementations, so the default suite does not need Atlas or AWS.

## Why the split

A route that opens its own Mongo collection is hard to test and easy to leak into the next feature. The protocol is the seam. Authentication still calls `UserRepository`. Phase 3 swaps the object behind that name from the in-memory class to `MongoUserRepository` for every environment except `test`.

## Users

The `users` collection stores `id` as `_id`, plus email, password hash, role, active flag, `created_at`, and `updated_at`. Email has a unique index created at startup. The index is not destructive. Passwords are stored only as Argon2id hashes.

`get_current_user` still loads the user after checking the JWT. That is one indexed read per authenticated request. The alternative is to trust the role claim inside the token. Trusting the claim skips the database and leaves a disabled or demoted user authorized until the token expires. The read is the choice that keeps Phase 2's immediate role changes.

## Documents

The `documents` collection stores metadata. The bytes live in S3 under `documents/{document_id}/{safe_filename}`. The client filename is reduced to one path segment before it is used. The API response does not include the object key, the bucket, or any credential.

Fields reserved for a later grant check:

- `owner_id`
- `allowed_roles`
- `allowed_user_ids`
- `tenant_id`

Phase 3 does not enforce those fields. Any authenticated user can list and download every document. Upload is admin and editor. Delete is admin only. An editor cannot delete, including a file they uploaded.

## Delete consistency

There is no distributed transaction between S3 and MongoDB.

1. The metadata row is marked `delete_pending`.
2. The S3 object is deleted. A missing object counts as already deleted, so a retry can continue.
3. The metadata row is deleted.

The HTTP call succeeds only after step 3. If step 2 or 3 fails, the response is `503` and the row remains so the client can retry. If step 3 fails after the object is gone, the row stays `delete_pending` instead of reporting success and forgetting the key.

Upload writes S3 first and then MongoDB. If the metadata insert fails, the service deletes the object it just wrote. If that cleanup also fails, the log records the document id and the client still receives an error.

## Startup

Outside `APP_ENV=test`, missing MongoDB or S3 settings stop the process with a message that names the variables and does not print their values. A connection failure raises `MongoDB or object storage is unavailable.` Driver exceptions are not returned to clients. Logs record an exception type, not the URI.

## Atlas network

The API connects out to the URI in `MONGODB_URI`. Atlas Network Access has to allow that client. The allowed address is an Atlas setting, not a value in this repository. Use a database user with `readWrite` on `MONGODB_DATABASE` only, not an Atlas organization administrator.
