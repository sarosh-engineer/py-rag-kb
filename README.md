# genai-rag-assistant

Document-based GenAI assistant for retrieval-augmented question answering, with authentication, role-based access, and citations.

This repository is in **Phase 1: foundation**. The running system is a FastAPI process with configuration, structured logging, a health check, and tests. Authentication, document storage, retrieval, the Angular client, and cloud deployment are later phases.

The GitHub repository is `py-rag-kb`. The application name is `genai-rag-assistant`.

## Phase 1 scope

Included:

- FastAPI application factory
- Pydantic Settings loaded from the environment
- `GET /health`
- JSON logs on stdout, with request id, status, and latency
- Safe error responses that do not return stack traces
- Explicit CORS allowlist
- pytest suite
- Container image that runs as a non-root user

Not included yet:

- AWS S3, Bedrock, ECR, or CloudWatch
- MongoDB Atlas
- Authentication and RBAC
- Document upload and RAG
- Angular frontend
- GitHub Actions and Kubernetes

## Repository layout

```text
backend/                 Python API. Run commands from this directory.
  app/                   Application package.
    api/                 Thin HTTP routes.
    schemas/             Public request and response models.
    services/            Business logic. Empty until the next phases.
    repositories/        Database and object-storage access. Empty for now.
    security/            Future JWT and RBAC dependencies.
    rag/                 Future retrieval and generation pipeline.
  tests/
infra/                  Reserved directories for later deployment work.
docs/architecture/      Current and target design.
docs/api/               HTTP contract notes.
docs/decisions/         Architecture decision records.
```

`frontend/` is intentionally absent until the client phase. Empty feature packages are real module boundaries, not placeholder implementations.

## Run locally

Python 3.12 is required.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp ../.env.example ../.env
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
docker build -t genai-rag-assistant:phase1 backend
docker run --rm -p 8000:8000 genai-rag-assistant:phase1
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

`CORS_ALLOWED_ORIGINS=*` is rejected. An empty value allows no browser origin.

## Security notes for this phase

- Secrets are not stored in source. `.env` is gitignored.
- API responses do not include stack traces or raw exception text.
- Validation errors do not echo the submitted value.
- Logs omit the query string. A redaction helper covers a few common secret patterns if a message contains one.
- CORS must list exact origins.
- Production mode disables `/docs` and `/openapi.json`.
- The container process runs as user `app`.

These controls do not replace authentication. There is no user identity in Phase 1.

## Where to read next

- [Architecture overview](docs/architecture/overview.md)
- [Phase 1 design](docs/architecture/phase-1.md)
- [Health API](docs/api/health.md)
- [ADR 0001: modular monolith](docs/decisions/0001-modular-monolith.md)
- [ADR 0002: runtime foundations](docs/decisions/0002-phase1-runtime-foundations.md)
