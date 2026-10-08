# ADR 0001: Start as a modular monolith

## Status

Accepted for Phase 1.

## Decision

The backend is one FastAPI process with separate packages for routes, schemas, services, repositories, security, and RAG.

## Why

The product needs authentication, document processing, and retrieval to share one user and document model. Putting those behind HTTP services now would add deployment and failure behavior before there is a scaling measurement. Package boundaries still keep database code out of routes, which is the split that usually matters first.

A microservice split remains possible later. The likely first candidate is document processing, because extraction and embedding are slower than chat requests. That split is not justified by the current code.

## Consequences

- One Dockerfile and one process health check.
- Shared settings and logging.
- No network contract between internal modules yet.
- In-process calls are normal Python calls, which unit tests can exercise without containers.
