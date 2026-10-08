# ADR 0004: MongoDB Atlas and S3 behind repositories

## Status

Accepted for Phase 3.

## Decision

1. Users and document metadata are stored in MongoDB Atlas through repository classes.
2. File bytes are stored in one S3 bucket through an `ObjectStorage` protocol.
3. `APP_ENV=test` keeps using in-memory doubles. The default pytest run does not need cloud credentials.
4. Live checks are opt-in with `RUN_INTEGRATION_TESTS=1`.
5. PyMongo's async client is used for database calls. boto3 stays synchronous and runs in a worker thread. Motor is not added.
6. Authenticated requests still load the user from the repository after the JWT is verified.
7. Delete is admin-only. Editor upload does not imply editor delete.

## Why repositories

The auth service already depended on `UserRepository`. Replacing the in-memory class with `MongoUserRepository` keeps registration, login, and role checks on the same methods. Routes still do not contain queries. A test can pass a fake collection or the in-memory class without standing up Atlas.

## Why not Motor

Current PyMongo ships `AsyncMongoClient`. Adding Motor would be a second driver for the same database.

## Why reload the user

The token role is a snapshot. The users collection is the source of truth for `is_active` and `role`. One read per request is cheaper than serving a disabled account until expiry.

## Why S3 keys are generated

A client filename is untrusted. Using it as the full key allows `../` to escape the prefix the IAM policy is meant to cover. The key is `documents/{server id}/{single safe segment}`.

## Limits

Listing is not filtered by owner or tenant yet. The columns for that filter are stored and unused. S3 and MongoDB are not one transaction. The delete sequence is retryable and does not report success while either side remains.
