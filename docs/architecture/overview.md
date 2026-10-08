# Architecture overview

The target system is one modular backend and one Angular client. Phase 1 implements only the backend process shell.

## Target request flow

```text
Angular client
    |
    |  HTTPS, JWT in Authorization header
    v
FastAPI
    |-- security dependencies enforce RBAC
    |-- document routes store original files in S3
    |-- processing extracts, chunks, and embeds text
    |-- MongoDB Atlas stores users, metadata, chats, and vectors
    |-- retrieval filters chunks by the caller's document scope
    |-- Bedrock generates an answer with citations
    v
JSON response
```

Retrieval must not search the whole vector collection. A viewer, editor, and admin can all call chat, but each call may only retrieve chunks from documents that principal is allowed to read.

## Why a modular monolith

The first deployable unit is one API process. Routes, services, repositories, security, and RAG are separate packages so a later split is possible without first inventing network boundaries. A document upload does not need its own service until processing time or scaling data shows that it does.

See [ADR 0001](../decisions/0001-modular-monolith.md).

## Phase map

| Phase | Outcome |
| --- | --- |
| 1 | FastAPI, settings, logging, health, tests, container |
| Later | Authentication and RBAC |
| Later | Documents, S3, extraction, chunking |
| Later | Embeddings, Atlas Vector Search, Bedrock answers, citations |
| Later | Angular client |
| Later | GitHub Actions, AWS deployment, CloudWatch |
| Later | Kubernetes |

Phase 1 does not create cloud resources.

## Runtime shape today

```text
Client or probe
    |
    v
RequestContextMiddleware   request id, access log
    |
    v
CORSMiddleware             explicit origin allowlist
    |
    v
Route                      GET /health
    |
    v
JSON response
```

Unexpected exceptions are converted to a generic JSON error by the framework's outer error handler. The response does not include a traceback.

## Package responsibilities

| Package | Responsibility |
| --- | --- |
| `app.api` | Translate HTTP to a service call and a response model |
| `app.schemas` | Validate the public contract |
| `app.services` | Business decisions |
| `app.repositories` | MongoDB and S3 access |
| `app.security` | Password hashing, JWT, and role dependencies |
| `app.rag` | Chunking, embeddings, scoped retrieval, prompts, citations |
| `app.config` | Environment configuration |
| `app.dependencies` | Objects routes ask FastAPI to inject |

Dependency direction to keep:

```text
api -> services -> repositories
api -> security
services -> rag
rag -> repositories
```

Routes should not construct database clients. Repositories should not know about HTTP.
