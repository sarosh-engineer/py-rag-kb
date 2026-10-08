# genai-rag-assistant

Document-based GenAI assistant for retrieval-augmented question answering, with authentication, role-based access, and citations.

This repository is in **Phase 3: MongoDB Atlas, S3, and configuration**. Accounts persist in MongoDB. Document bytes live in S3. Document metadata lives in MongoDB. Retrieval, embeddings, the Angular client, and cloud deployment are later phases.

The GitHub repository is `py-rag-kb`. The application name is `genai-rag-assistant`.

## Current scope

Included:

- FastAPI application factory, settings, JSON logs, and `GET /health`
- Registration, login, and `GET /auth/me` against MongoDB
- Argon2id password hashes and short-lived JWT access tokens
- Backend role checks for admin, editor, and viewer
- Admin user list and role or active-flag changes
- Authenticated document upload, list, download, and delete
- pytest suite that does not need Atlas or AWS credentials
- Container image that runs as a non-root user and does not contain secrets

Not included yet:

- Bedrock, embeddings, vector search, chunking, or text extraction
- Document-level authorization (the fields are stored and not enforced)
- Angular frontend
- GitHub Actions, Kubernetes, and ECR

## Architecture

```text
FastAPI route
    |
    v
Service layer          AuthService, DocumentService
    |
    +--> Repository     UserRepository, DocumentRepository
    |                        |
    |                        +--> MongoDB Atlas (users, documents)
    |
    +--> ObjectStorage
                             |
                             +--> AWS S3 (file bytes)
```

Routes do not import PyMongo or boto3. Services depend on the protocols. `create_app` selects the implementation: MongoDB and S3 outside tests, in-memory doubles when `APP_ENV=test`. That split keeps the default test suite free of production credentials and keeps a storage change from spreading through the HTTP layer.

Details: [storage architecture](docs/architecture/storage.md) and [ADR 0004](docs/decisions/0004-mongodb-and-s3.md).

## Repository layout

```text
backend/                 Python API. Run commands from this directory.
  app/                   Application package.
    api/                 Thin HTTP routes.
    schemas/             Public request and response models.
    services/            Registration, login, and document operations.
    repositories/        User and document storage contracts and MongoDB classes.
    storage/             Object storage contract and the S3 class.
    security/            Password hashing, JWT, and role dependencies.
    rag/                 Future retrieval and generation pipeline.
  tests/unit/            Fakes and API tests. No cloud credentials.
  tests/integration/     Opt-in live Atlas and S3 checks.
infra/aws/               Recommended S3 IAM policy. Not applied by the app.
docs/architecture/      Current and target design.
docs/api/               HTTP contract notes.
docs/decisions/         Architecture decision records.
```

`frontend/README.md` describes the future Angular login flow. The client is not built yet. The API never returns AWS keys to a client.

## Run locally

Python 3.12 is required.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp ../.env.example ../.env
```

Edit `.env` at the repository root. Never commit it. Required names and placeholders are at the end of this file. Generate a signing key with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Then start the API from `backend/`:

```bash
python -m app
```

`python -m app` reads `HOST` and `PORT` and disables Uvicorn's second access log. The same process can be started explicitly:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Open `http://127.0.0.1:8000/health`. Interactive docs are at `http://127.0.0.1:8000/docs` when `APP_ENV` is not `production`.

Settings are read from the process environment. For local development, a `.env` file at the repository root is also read. A missing MongoDB or S3 setting stops startup with a message that names the variables and does not print their values. `APP_ENV=test` skips those stores and uses memory, which is how the test suite runs.

## MongoDB Atlas setup

1. Create a database user that can `readWrite` the database named by `MONGODB_DATABASE` (the example value is `genai_rag`). Do not use an Atlas organization administrator for the application.
2. Put that user's connection string in `MONGODB_URI`. The value stays in `.env` or the process environment.
3. In Atlas Network Access, allow the address of the machine that runs the API. That address is an Atlas setting. Do not hard-code it in this repository. A Cursor Cloud Agent or any other host needs its own allow entry before a non-test process can connect.
4. On startup the API creates a unique index on `users.email` and indexes on `documents.uploaded_by` and `documents.owner_id`. Index creation is not destructive. Collections are `users` and `documents`. There is no vector index in this phase.

## S3 setup

1. Create one bucket in the region named by `AWS_REGION`.
2. Create an IAM user or role with only the permissions in [infra/aws/README.md](infra/aws/README.md). Do not attach `AdministratorAccess`. Do not use the AWS account root user. Do not add Bedrock or EKS permissions yet.
3. Supply `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, and `S3_BUCKET_NAME` at runtime. The process uses those values to build a boto3 client. They are not returned by any route.

Startup calls `HeadBucket`, which needs `s3:ListBucket` on the bucket. Uploads, downloads, and deletes need `s3:PutObject`, `s3:GetObject`, and `s3:DeleteObject` on `arn:aws:s3:::YOUR_BUCKET/*`.

## Run the tests

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

The default suite uses in-memory repositories and storage. It does not call Atlas or AWS. Live checks live in `tests/integration/` and stay skipped unless you set `RUN_INTEGRATION_TESTS=1` and provide real credentials in the environment. Do not enable that in a default CI job that lacks those credentials.

## Run the container

```bash
docker build -t genai-rag-assistant:phase3 backend
docker run --rm -p 8000:8000 --env-file .env genai-rag-assistant:phase3
```

Pass environment variables at runtime. The image does not copy `.env`. `backend/.dockerignore` excludes `.env` and `.env.*`. The image binds to `0.0.0.0`. The local process defaults to `127.0.0.1`.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_NAME` | `genai-rag-assistant` | Service name returned by `/health` |
| `APP_ENV` | `local` | `local`, `test`, `development`, `staging`, or `production` |
| `APP_VERSION` | `0.1.0` | Version returned by `/health` |
| `LOG_LEVEL` | `INFO` | Root logger level |
| `LOG_JSON` | `true` | JSON logs when true; plain text when false |
| `HOST` | `127.0.0.1` | Bind address for `python -m app` |
| `PORT` | `8000` | Port for `python -m app` |
| `CORS_ALLOWED_ORIGINS` | empty | Comma-separated `http` or `https` origins |
| `JWT_SECRET_KEY` | empty | HMAC signing key. Required in production. At least 32 characters |
| `JWT_ALGORITHM` | `HS256` | `HS256`, `HS384`, or `HS512` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime, from 5 to 1440 minutes |
| `BOOTSTRAP_ADMIN_EMAIL` | empty | Optional initial admin email |
| `BOOTSTRAP_ADMIN_PASSWORD` | empty | Optional initial admin password. Set both bootstrap values or neither |
| `MONGODB_URI` | empty | Atlas connection string. Required outside `APP_ENV=test` |
| `MONGODB_DATABASE` | `genai_rag` | Database name. Not hard-coded in repositories |
| `AWS_REGION` | empty | Region for the S3 client |
| `AWS_ACCESS_KEY_ID` | empty | IAM access key id. Required outside tests |
| `AWS_SECRET_ACCESS_KEY` | empty | IAM secret key. Required outside tests |
| `S3_BUCKET_NAME` | empty | Bucket that stores document bytes |
| `MAX_UPLOAD_BYTES` | `10485760` | Upload limit, 10 MiB |

`CORS_ALLOWED_ORIGINS=*` is rejected. An empty value allows no browser origin.

## Authentication persistence

Registration, login, and account updates go through `AuthService` and `UserRepository`. Outside tests that repository is `MongoUserRepository`. The `users` collection stores the id, email, Argon2id password hash, role, active flag, `created_at`, and `updated_at`. Email is unique. Plaintext passwords are not stored.

Public registration still creates a viewer. A caller cannot submit a role. Disabled users cannot authenticate. `GET /auth/me` and other protected routes validate the JWT and then load the user. The role and active flag in MongoDB are authoritative. Trusting the JWT role claim would skip that read and would leave a disabled or demoted user authorized until the token expired. The extra indexed read is the tradeoff that keeps role changes immediate.

## Roles

| Capability | Admin | Editor | Viewer |
| --- | --- | --- | --- |
| List and download documents | yes | yes | yes |
| Upload documents | yes | yes | no |
| Delete documents | yes | no | no |
| Manage users and roles | yes | no | no |

Listing and download are coarse in this phase: any authenticated user can read every document. Owner and tenant fields are stored for a later check. An editor cannot delete a document, including one they uploaded.

`GET /protected/user`, `GET /protected/editor`, and `GET /protected/admin` remain demonstration routes.

## Example requests

Register and sign in:

```bash
curl -s -X POST http://127.0.0.1:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"viewer@example.com","password":"viewer-password-1"}'

curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"viewer@example.com","password":"viewer-password-1"}'
```

Call a protected route with the `access_token` from the login response:

```bash
curl -s http://127.0.0.1:8000/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Upload, list, download, and delete (admin or editor for upload; admin for delete):

```bash
curl -s -X POST http://127.0.0.1:8000/documents \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@notes.txt;type=text/plain"

curl -s http://127.0.0.1:8000/documents \
  -H "Authorization: Bearer $ACCESS_TOKEN"

curl -s -D - http://127.0.0.1:8000/documents/$DOCUMENT_ID/content \
  -H "Authorization: Bearer $ACCESS_TOKEN" -o notes.txt

curl -s -o /dev/null -w "%{http_code}" -X DELETE \
  http://127.0.0.1:8000/documents/$DOCUMENT_ID \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

The upload response is metadata. It does not include the S3 key, the bucket, or credentials. More status codes: [document API](docs/api/documents.md).

## Security

- Credentials come from the environment. `.env` is gitignored. `.env.example` has empty secret values.
- Password hashes are stored. Passwords and hashes are not returned and are not placed in the JWT.
- Login uses one error for an unknown email, a wrong password, and a disabled account.
- API responses do not include stack traces or driver exception text. A failed Atlas or S3 connection is reported as `MongoDB or object storage is unavailable.`
- Logs omit the query string, the password, the bearer token, and MongoDB URIs.
- Object keys are `documents/{document_id}/{safe_filename}`. The filename is one path segment. `../` and other unsafe characters are not used as key structure.
- CORS allows `Authorization`, `Content-Type`, and `X-Request-ID`, and the methods the API serves.
- Production mode disables `/docs` and `/openapi.json` and refuses to start without a long enough signing key.
- The container process runs as user `app`. The image does not contain `.env`.
- The Angular client, when it exists, must not receive AWS access keys.

`GET /health` only means this process answered. It does not probe Atlas or S3.

## Known limitations

- Document ACL fields are not enforced. Any signed-in user can list and download every file.
- S3 and MongoDB are not one transaction. Delete marks the row `delete_pending`, deletes the object, then deletes the row. Success is `204` only when both are gone. A failure returns `503` and leaves the row so the caller can retry. Upload deletes the new object if the metadata insert fails; if that cleanup also fails, the object can remain without a row and the client still receives an error.
- `HeadBucket` at startup needs `s3:ListBucket`. A missing object on download is `404`. A missing object on delete is treated as already removed so a retry can finish the metadata delete.
- Several API processes share Atlas and the bucket. They do not share the in-memory stores used when `APP_ENV=test`.
- There is no text extraction, chunking, embedding, or vector index.

## Where to read next

- [Architecture overview](docs/architecture/overview.md)
- [MongoDB and S3](docs/architecture/storage.md)
- [Authentication](docs/architecture/authentication.md)
- [Auth API](docs/api/auth.md)
- [Document API](docs/api/documents.md)
- [Health API](docs/api/health.md)
- [S3 IAM policy](infra/aws/README.md)
- [ADR 0004: MongoDB and S3](docs/decisions/0004-mongodb-and-s3.md)

## Environment variable names

Copy `.env.example` to `.env`. Fill values locally. Do not commit `.env`.

```text
MONGODB_URI=
MONGODB_DATABASE=genai_rag

AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
S3_BUCKET_NAME=

JWT_SECRET_KEY=
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Optional, from earlier phases: `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` (both or neither), plus `APP_ENV`, `APP_NAME`, `LOG_LEVEL`, `LOG_JSON`, `HOST`, `PORT`, `CORS_ALLOWED_ORIGINS`, and `MAX_UPLOAD_BYTES`.
