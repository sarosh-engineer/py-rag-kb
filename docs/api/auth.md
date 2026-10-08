# Authentication API

Interactive docs are at `/docs` when `APP_ENV` is not `production`. Use the Authorize button and the access token from `POST /auth/login`. The scheme is HTTP bearer.

## POST /auth/register

Creates an active viewer. Does not return a token.

```json
{ "email": "viewer@example.com", "password": "viewer-password-1" }
```

Password length is 12 to 128 characters, with at least one letter and one digit.

| Status | Code | When |
| --- | --- | --- |
| 201 | | Account created |
| 409 | `email_taken` | Email already registered |
| 422 | `validation_error` | Invalid email, weak password, or unexpected field such as `role` |
| 503 | `auth_not_configured` | `JWT_SECRET_KEY` is missing or shorter than 32 characters |

## POST /auth/login

```json
{ "email": "viewer@example.com", "password": "viewer-password-1" }
```

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "...",
    "email": "viewer@example.com",
    "role": "viewer",
    "is_active": true,
    "created_at": "2026-10-08T00:00:00Z"
  }
}
```

Unknown email, wrong password, and disabled account all return `401` `invalid_credentials` with the message `Invalid email or password.`

## GET /auth/me

Requires `Authorization: Bearer <access_token>`.

Missing, expired, malformed, and inactive-account tokens return `401` `unauthorized` and `WWW-Authenticate: Bearer`. The message is `Authentication is required.`

## GET /users

Admin only. Returns the public account fields.

## PATCH /users/{user_id}

Admin only.

```json
{ "role": "editor", "is_active": true }
```

An admin cannot demote or disable their own account (`400` `cannot_change_self`).

## Demonstration routes

| Method and path | Allowed roles |
| --- | --- |
| `GET /protected/user` | any active account |
| `GET /protected/editor` | admin, editor |
| `GET /protected/admin` | admin |

These routes exist to exercise RBAC. They are not product features.
