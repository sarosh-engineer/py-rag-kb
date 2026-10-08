# Phase 1 design

## What was built

The backend is an application factory, `create_app`. Uvicorn serves the object created at import time. Tests build another instance with an explicit `Settings` object, so a developer machine's environment does not decide the test result.

`GET /health` is a liveness check. It reports the configured service name, environment, and version. It does not connect to a database or cloud API, because those dependencies do not exist yet. A readiness check can be added when a failed dependency should remove the process from a load balancer.

## Logging

Each HTTP request writes one access log line with:

- `request_id`
- `method`
- `path`
- `status_code`
- `duration_ms`

The query string is not logged. Document text, prompts, and credentials are out of scope for logs. `redact_text` removes a few obvious secret shapes if they appear in a message or traceback. That helper is a backstop.

JSON goes to stdout so the same code works on a laptop and, later, under CloudWatch. The module is `app.logging_config` rather than `app.logging` so it does not shadow Python's standard `logging` module.

Uvicorn's own access log is disabled with `--no-access-log`. Otherwise the process would emit a second, unstructured line for every request.

## Errors

Successful and expected HTTP errors pass through the request middleware, which sets `X-Request-ID`.

Unexpected exceptions are handled by Starlette's outermost server-error middleware. That middleware sits outside both the request middleware and the CORS middleware. The unhandled-error handler therefore sets `X-Request-ID` itself and, when the browser origin is on the allowlist, `Access-Control-Allow-Origin`.

The client body is always:

```json
{
  "error": {
    "code": "internal_error",
    "message": "An unexpected error occurred.",
    "request_id": "..."
  }
}
```

## CORS

`CORS_ALLOWED_ORIGINS` is a comma-separated list of `http` and `https` origins. `*` is invalid. An empty list means a browser on another origin cannot read responses. The Phase 1 allowlist permits `GET` and `OPTIONS`, and the headers `Content-Type` and `X-Request-ID`. A later phase that adds `POST` or `Authorization` must extend this list on purpose.

## Container

The image installs `backend/requirements.txt`, copies the `app` package, and runs as `app`. Tests and development tools are not in the image. The container health check calls `/health`.

`python -m app` binds `HOST` and `PORT`, which default to `127.0.0.1:8000`. The image command is `uvicorn --host 0.0.0.0` instead. Using the local default inside a container would publish a port that nothing outside the container could reach.

## What this phase is meant to teach

- A factory function makes the process testable without a global configuration.
- Settings, logging, and error shape are cross-cutting and should exist before feature code.
- Authorization will be a dependency next to `get_settings`, not a condition in the Angular templates.
- Empty packages record the intended boundaries before the implementations arrive.
