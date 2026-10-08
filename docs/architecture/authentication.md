# Authentication and RBAC

Phase 2 identifies the caller. It does not store documents.

## Request flow

```text
Angular
    |
    |  POST /auth/login  { email, password }
    v
FastAPI AuthService
    |
    |  Argon2id verify, then sign a JWT
    v
Angular stores the access token
    |
    |  Authorization: Bearer <token>
    v
get_current_user
    |
    |  verify signature and expiry, load the user, reject inactive accounts
    v
require_roles(...)
    |
    v
route
```

Angular will later use `user.role` to choose routes, hide navigation, and show admin screens. That is presentation. A viewer who calls `PATCH /users/{id}` directly receives `403`. The dependency on the route is the control.

## Token

The access token is HS256 by default. The payload is:

| Claim | Meaning |
| --- | --- |
| `sub` | User id |
| `role` | Role at the time the token was issued |
| `typ` | `access` |
| `iat` | Issued-at time |
| `exp` | Expiry |

The role claim is checked for shape. Authorization uses the role currently stored for `sub`. An admin change applies on the next request, before the token expires. Disabling the account makes the token stop working.

The token does not contain the email, the password, or the password hash.

## Roles

`require_roles` is an allow-list. Admin is not implied. `GET /protected/editor` lists `Role.ADMIN` and `Role.EDITOR`.

| Capability | Admin | Editor | Viewer |
| --- | --- | --- | --- |
| Sign in and call `GET /auth/me` | yes | yes | yes |
| `GET /protected/user` | yes | yes | yes |
| `GET /protected/editor` | yes | yes | yes |
| `GET /protected/admin` | yes | no | no |
| List users and change roles | yes | no | no |
| Future chat and authorized document read | yes | yes | yes |
| Upload a document | yes | yes | no |
| Delete a document | yes | no | no |

`/protected/*` routes are demonstrations. They can be removed when real chat and document routes exist.

Public `POST /auth/register` always creates an active viewer. The body has no role field, and extra fields are rejected. The first admin comes from `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD`, or from an existing admin calling `PATCH /users/{id}`.

## Persistence

`UserRepository` is the storage contract. `MongoUserRepository` implements it for every environment except `test`. `InMemoryUserRepository` remains the test double. `create_app` chooses the implementation and stores it on `app.state`. User ids are strings so the API does not depend on MongoDB `ObjectId`. See [storage](storage.md).

## Document authorization later

```text
User
  -> Role                         who they are
  -> document grants              which documents they may read
  -> retriever filter             chunks from those documents only
  -> prompt and answer
```

A role does not grant every document. The retriever must receive the caller's allowed document ids. That filter is not implemented yet.

## Frontend storage

The API expects the token in the `Authorization` header. It does not set a cookie, and CORS stays `allow_credentials=false`. When the Angular client is added, a script-accessible token can be stolen by XSS. Route guards do not fix that. The API checks the token again.
