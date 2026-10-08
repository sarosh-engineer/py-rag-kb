# genai-rag-assistant

Document-based GenAI assistant for retrieval-augmented question answering, with authentication, role-based access, and citations.

This repository is in **Phase 2: authentication and RBAC**. The API has configuration, structured logging, a health check, registration, JWT login, and role checks enforced on the server. Document storage, retrieval, the Angular client, and cloud deployment are later phases.

The GitHub repository is `py-rag-kb`. The application name is `genai-rag-assistant`.

## Current scope

Included:

- FastAPI application factory, settings, JSON logs, and `GET /health`
- Registration, login, and `GET /auth/me`
- Argon2id password hashes and short-lived JWT access tokens
- Backend role checks for admin, editor, and viewer
- Admin user list and role or active-flag changes
- pytest suite, including authentication and RBAC
- Container image that runs as a non-root user

Not included yet:

- AWS S3, Bedrock, ECR, or CloudWatch
- MongoDB Atlas (users are in a temporary in-memory store)
- Document upload, document ACLs, and RAG
- Angular frontend
- GitHub Actions and Kubernetes

## Repository layout

```text
backend/                 Python API. Run commands from this directory.
  app/                   Application package.
    api/                 Thin HTTP routes.
    schemas/             Public request and response models.
    services/            Registration, login, and account changes.
    repositories/        User storage contract and the temporary in-memory store.
    security/            Password hashing, JWT, and role dependencies.
    rag/                 Future retrieval and generation pipeline.
  tests/
infra/                  Reserved directories for later deployment work.
docs/architecture/      Current and target design.
docs/api/               HTTP contract notes.
docs/decisions/         Architecture decision records.
```

`frontend/README.md` describes the future Angular login flow. The client is not built yet. RAG and document packages are still boundaries without implementations.

## Run locally

Python 3.12 is required.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp ../.env.example ../.env
```

Edit `.env` and set `JWT_SECRET_KEY` to a random value of at least 32 characters. Login returns `503` until that key is present. Generate one with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Optional first administrator, also in `.env`:

```text
BOOTSTRAP_ADMIN_EMAIL=admin@example.com
BOOTSTRAP_ADMIN_PASSWORD=replace-with-a-real-password-1
```

Then start the API:

```bash
python -m app
```

`python -m app` reads `HOST` and `PORT` and disables Uvicorn's second access log. The same process can be started explicitly:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Open `http://127.0.0.1:8000/health`. Interactive docs are at `http://127.0.0.1:8000/docs` when `APP_ENV` is not `production`.

Settings are read from the process environment. For local development, a `.env` file at the repository root is also read. Never commit that file.

## Run the tests

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

## Run the container

```bash
docker build -t genai-rag-assistant:phase2 backend
docker run --rm -p 8000:8000 -e JWT_SECRET_KEY genai-rag-assistant:phase2
```

The image binds to `0.0.0.0` inside the container. The local process defaults to `127.0.0.1`.

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

`CORS_ALLOWED_ORIGINS=*` is rejected. An empty value allows no browser origin.

The container image installs `backend/requirements.txt` and runs the same process. Pass `JWT_SECRET_KEY` into the container at runtime. Do not bake it into the image.

## Authentication

Passwords are hashed with Argon2id. A login that succeeds returns a bearer JWT. Protected routes declare `get_current_user` or `require_roles(...)`. The dependency loads the user from the repository, so a disabled account or a changed role takes effect on the next request.

Public registration creates a viewer. Sending `"role": "admin"` is a validation error. An administrator is created from the bootstrap environment variables, or by an admin calling `PATCH /users/{id}`.

Details: [authentication architecture](docs/architecture/authentication.md) and [ADR 0003](docs/decisions/0003-authentication-and-rbac.md).

## Roles

| Capability | Admin | Editor | Viewer |
| --- | --- | --- | --- |
| Chat and read authorized documents (later) | yes | yes | yes |
| Upload documents (later) | yes | yes | no |
| Delete documents (later) | yes | no | no |
| Manage users and roles | yes | no | no |

`GET /protected/user`, `GET /protected/editor`, and `GET /protected/admin` are demonstration routes for these checks. They are safe to remove later.

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

In Swagger (`/docs`), choose Authorize and paste the access token.

## Security

- The signing key and the bootstrap password come from the environment. `.env` is gitignored. `.env.example` has empty values.
- Password hashes are stored. Passwords and hashes are not returned and are not placed in the JWT.
- Login uses one error for an unknown email, a wrong password, and a disabled account.
- API responses do not include stack traces.
- Logs omit the query string and do not record the password or the bearer token.
- CORS allows `Authorization`, `Content-Type`, and `X-Request-ID`, and only the methods the API serves.
- Production mode disables `/docs` and `/openapi.json` and refuses to start without a long enough signing key.
- The container process runs as user `app`.

Frontend route guards are not a security boundary. See [frontend/README.md](frontend/README.md).

## Temporary user store

`InMemoryUserRepository` keeps accounts in the API process. Restarting the process deletes them. Several workers do not share the same users. This class is the stand-in until a `MongoUserRepository` implements the same `UserRepository` methods and `create_app` constructs that class instead. The HTTP API does not need to change for that swap.

## Where to read next

- [Architecture overview](docs/architecture/overview.md)
- [Authentication](docs/architecture/authentication.md)
- [Auth API](docs/api/auth.md)
- [Health API](docs/api/health.md)
- [Phase 1 design](docs/architecture/phase-1.md)
- [ADR 0001: modular monolith](docs/decisions/0001-modular-monolith.md)
- [ADR 0002: runtime foundations](docs/decisions/0002-phase1-runtime-foundations.md)
- [ADR 0003: authentication and RBAC](docs/decisions/0003-authentication-and-rbac.md)
