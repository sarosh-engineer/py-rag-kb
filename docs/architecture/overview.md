# Architecture overview

The target system is one modular backend and one Angular client. Phase 1 is the process shell. Phase 2 adds accounts, JWT access tokens, and backend role checks. Phase 3 stores those accounts and document metadata in MongoDB Atlas and stores file bytes in S3. Retrieval and generation are still later work.

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

Retrieval must not search the whole vector collection. A viewer, editor, and admin can all call chat, but each call may only retrieve chunks from documents that principal is allowed to read. Phase 3 stores owner, allowed roles, allowed users, and a tenant id on each document, and does not enforce them yet. The retriever, when it exists, must take the allowed document ids from an authorization service rather than from the model.

## Why a modular monolith

The first deployable unit is one API process. Routes, services, repositories, security, and RAG are separate packages so a later split is possible without first inventing network boundaries. A document upload does not need its own service until processing time or scaling data shows that it does.

See [ADR 0001](../decisions/0001-modular-monolith.md).

## Phase map

| Phase | Outcome |
| --- | --- |
| 1 | FastAPI, settings, logging, health, tests, container |
| 2 | Registration, JWT access tokens, backend RBAC |
| 3 | MongoDB users and document metadata, S3 file storage |
| Later | Extraction, chunking, embeddings, vector search |
| Later | Embeddings, Atlas Vector Search, Bedrock answers, citations |
| Later | Angular client |
| Later | GitHub Actions, AWS deployment, CloudWatch |
| Later | Kubernetes |

The application does not create IAM users or Atlas network rules.

## Runtime shape today

```text
Client
    |
    v
RequestContextMiddleware   request id, access log
    |
    v
CORSMiddleware             explicit origin allowlist
    |
    v
Route                      health, auth, users, documents
    |
    v
Service
    |
    +--> UserRepository / DocumentRepository --> MongoDB Atlas
    |
    +--> ObjectStorage --> S3
```

`APP_ENV=test` uses in-memory doubles for those three stores. See [storage](storage.md).

Unexpected exceptions are converted to a generic JSON error by the framework's outer error handler. The response does not include a traceback.

## Package responsibilities

| Package | Responsibility |
| --- | --- |
| `app.api` | Translate HTTP to a service call and a response model |
| `app.schemas` | Validate the public contract |
| `app.services` | Business decisions |
| `app.repositories` | MongoDB access behind repository protocols |
| `app.storage` | S3 access behind the object-storage protocol |
| `app.security` | Password hashing, JWT, and role dependencies |
| `app.rag` | Chunking, embeddings, scoped retrieval, prompts, citations |
| `app.config` | Environment configuration |
| `app.dependencies` | Objects routes ask FastAPI to inject |

Dependency direction to keep:

```text
api -> services -> repositories
api -> services -> storage
api -> security
services -> rag
rag -> repositories
```

Routes should not construct database clients. Repositories should not know about HTTP.
