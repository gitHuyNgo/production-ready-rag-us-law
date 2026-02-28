# Authentication & User Management Architecture

This document outlines the architecture and data flows for the auth-api, user-api, and the API Gateway.

## Architectural Overview

User identity, security, and profile management are handled by a decoupled microservices setup behind a single API Gateway.

- **API Gateway**: Single entry point. Validates JWT (RS256 with auth-api’s public key), rate limits, and proxies to backend services. Does not store user data.
- **Auth API**: Identity, credentials, JWT issuance, refresh tokens, and OIDC (e.g. Google). Uses PostgreSQL (or in-memory fallback when DB is unavailable).
- **User API**: Profile CRUD (display name, bio, etc.). Uses MongoDB. Validates JWT with the same public key; does not store passwords.
- **Event streaming (optional)**: Auth-api can publish `UserCreated` events (e.g. to Kafka) for downstream provisioning; in light setups this may be in-memory or disabled.

---

## 1. Auth API

The Auth API is responsible for identity verification and token lifecycle.

### Security

- **RS256**: Private key (PEM) signs access tokens; public key (PEM) is used by the gateway and user-api to verify. Configure via `JWT_PRIVATE_KEY` / `JWT_PRIVATE_KEY_PATH` and `JWT_PUBLIC_KEY` / `JWT_PUBLIC_KEY_PATH`.
- **Passwords**: Argon2 (Passlib); only hashes are stored.
- **Refresh tokens**: Stored in PostgreSQL (one per user, updated on login); used to issue new access tokens without re-entering password.

### Data Model (PostgreSQL / SQLAlchemy)

When `AUTH_DB_URL` is set and init succeeds, the following models are used:

- **UserModel** (`users`): `username` (PK), `email`, `password` (hash).
- **FederatedModel** (`federated`): `provider`, `subject_id` (PK), `user_id` — OIDC mapping.
- **RefreshTokenModel** (`refresh_tokens`): `user_id` (PK), `token`, `expires_at`, `revoked`.

When DB is unavailable, `PostgreAuthRepository` uses a shared **in-memory** dict so register and login still work (e.g. tests, dev without Postgres).

### Flows

- **Register**: POST `/auth/register` with username, email, password → hash password, create user, (optionally) publish UserCreated.
- **Login**: POST `/auth/token` (form: username, password) → verify credentials, create access + refresh tokens, set refresh_token cookie, store refresh token in DB.
- **Me**: GET `/auth/me` with Bearer token → decode JWT, load user by `sub`, return username/email.
- **OIDC (Google)**: GET `/auth/login/google` → redirect to Google; GET `/auth/callback/google?code=...` → exchange code, validate id_token, find or create user and federated row, set cookies and redirect with app tokens.

---

## 2. User API

- **Role**: Application-level user profile data only. No passwords or credentials.
- **Storage**: MongoDB; documents keyed by `user_id` (JWT `sub`).
- **Auth**: Every request requires a valid Bearer token; user-api verifies it with the auth-api public key and uses `sub` as the profile id.
- **Endpoints**: GET/PUT `/profiles/me` to read and update the current user’s profile.

---

## 3. Gateway

- Validates JWT on protected routes; public routes (e.g. `/auth/register`, `/auth/token`, `/health`) do not require a token.
- Forwards requests to auth-api, user-api, or chat-api and adds `X-User-Id` when the token is valid.
- See [API Gateway](../api/api-gateway.md) for routing and proxy details.
