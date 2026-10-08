# Frontend

The Angular client is not part of this phase.

When it is added, login will be:

```text
Angular  -- POST /auth/login -->  FastAPI
Angular  <-- access token -----  FastAPI
Angular  -- Authorization: Bearer <token> -->  FastAPI
```

The client can read `user.role` to guard routes, hide navigation, and show admin-only screens. Those checks are presentation. FastAPI dependencies are the authorization control. A hidden button does not stop a direct request.

The API does not set an auth cookie. The client sends the bearer token. Do not put AWS credentials or the JWT signing key in the frontend.
