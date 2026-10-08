# ADR 0002: Phase 1 runtime foundations

## Status

Accepted for Phase 1.

## Decision

1. Configuration uses Pydantic Settings and environment variables.
2. Logs are structured JSON on stdout, implemented with the standard library.
3. `/health` is a liveness endpoint with no downstream checks.
4. API errors use one JSON object and never return a traceback.
5. CORS origins are an explicit allowlist. A wildcard is configuration failure.
6. Interactive API docs are disabled when `APP_ENV=production`.

## Why

These choices are hard to retrofit cleanly once routes start returning their own error shapes. They also match how the later AWS deployment should run: environment-injected secrets, stdout collected by the platform, and a probe that does not depend on Bedrock.

`structlog` was considered. The standard library is enough while the only context fields are request id, method, path, status, and duration. Moving to `structlog` stays possible if bound context becomes awkward.

A global settings object was rejected for tests. `create_app(settings)` receives the configuration for that instance. `load_settings()` remains the process-wide loader used by Uvicorn.

## Consequences

- `.env` is a local convenience. Production must inject real environment variables.
- Log redaction is best-effort. Call sites still must not log secrets or document text.
- Health being green does not prove that future dependencies are healthy.
- Production clients cannot browse `/docs` unless a later decision puts documentation behind authentication.
