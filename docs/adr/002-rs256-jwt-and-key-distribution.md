# ADR 002: RS256 JWT and Public Key Distribution

## Status

Accepted.

## Context

Access tokens must be verifiable by the API Gateway and User API without calling the Auth API on every request. Symmetric signing (HS256) would require sharing a secret with all verifiers and is less suitable for multi-service validation.

## Decision

- **Algorithm**: RS256 (RSA signature). Auth API signs tokens with a **private** key; Gateway and User API verify with the corresponding **public** key.
- **Configuration**:
  - **Auth API**: `JWT_PRIVATE_KEY` or `JWT_PRIVATE_KEY_PATH` to sign; `JWT_PUBLIC_KEY` or `JWT_PUBLIC_KEY_PATH` for `/me` and token validation when needed.
  - **API Gateway**: `JWT_PUBLIC_KEY` or `JWT_PUBLIC_KEY_PATH` (auth-api’s public key) to verify `Authorization: Bearer <token>` and WebSocket auth.
  - **User API**: Same public key via `JWT_PUBLIC_KEY` or `JWT_PUBLIC_KEY_PATH` to verify tokens on `/profiles/*`.
- **Deployment**: In Docker, auth-api mounts PEM files (e.g. `private.pem`, `public.pem`) into `/run/secrets/` and sets `JWT_*_PATH` accordingly. Gateway and user-api receive the same public key (copy or shared mount).

## Consequences

- No shared secret; only auth-api holds the private key. Compromise of gateway or user-api does not allow forging tokens.
- Key rotation: replace public key on gateway and user-api when auth-api keys are rotated.
- Tests: generate temporary RSA key pairs in CI (e.g. `openssl`) in `tests/fixtures/` so conftest can set `JWT_PUBLIC_KEY_PATH` / `JWT_PRIVATE_KEY_PATH` for tests.
