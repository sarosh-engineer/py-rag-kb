# ADR 0003: Authentication and backend RBAC

## Status

Accepted for Phase 2.

## Decision

1. Passwords are hashed with Argon2id through `pwdlib`. The application does not implement a password hash.
2. Sessions are short-lived signed JWTs (`PyJWT`), sent as `Authorization: Bearer`.
3. Every protected route declares `get_current_user` or `require_roles(...)`.
4. `require_roles` is an explicit allow-list. Admin is included only when the route lists `Role.ADMIN`.
5. The user row is reloaded on each authenticated request. The role claim in the token is not the permission decision.
6. Accounts are stored behind `UserRepository`. Phase 2 ships `InMemoryUserRepository` only.
7. Public registration creates viewers. Admin is assigned by bootstrap configuration or by an admin.

## Why JWT

The Angular client and the API are separate. A bearer token lets the client call the API without a server-side session table. The token is small and carries an expiry. Because the API still loads the user, disablement and role changes do not wait for that expiry. The cost is that a stolen token works until expiry or until the account is disabled. There is no refresh token in this phase.

## Why password hashing

A database copy must not be a list of passwords. Argon2id is memory-hard and is the algorithm `pwdlib.PasswordHash.recommended()` selects. Verification runs in a normal synchronous route so the hash work does not block the event loop; FastAPI runs that route in a threadpool.

## Why backend RBAC

The browser is not a trust boundary. Hiding an admin link does not stop `PATCH /users/{id}`. The dependency runs for every call, including calls made with curl.

## Why a repository

Auth routes need `get`, `add`, and `update`. Those operations are the same whether the body is a dict in this process or a MongoDB collection. The service depends on the protocol. `create_app` chooses the implementation. Replacing the store should not require a new login API.

## Why in-memory for now

MongoDB is a later phase, and Phase 1 had no database. An in-memory class keeps the tests free of external services and makes the temporary choice obvious. It is not durable, not shared across processes, and not a production user directory.

## Security limits that remain

- Restarting the process deletes accounts.
- There is no login rate limit or lockout.
- Registration returns `409` when the email exists. Login does not distinguish unknown, wrong, and disabled accounts.
- There is no refresh-token rotation or revocation list. Disabling the user is the revocation path.
- The signing key is symmetric. Key rotation is not implemented; changing the secret invalidates outstanding tokens.
- A token kept where page scripts can read it is exposed to XSS. That has to be handled when the client is built.
- Document-level grants are not enforced because documents do not exist yet.
