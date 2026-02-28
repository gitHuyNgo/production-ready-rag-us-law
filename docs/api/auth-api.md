# Auth API

The Auth API handles identity, credentials, and token lifecycle. It is exposed via the gateway at `/auth/*`.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | No | Register with username, email, password. Returns user info (username, email). |
| POST | `/auth/token` | No | Login with form body `username` and `password` (OAuth2 form). Returns `access_token` and `refresh_token`; sets `refresh_token` cookie (httponly, lax). |
| GET | `/auth/me` | Bearer | Returns current user (username, email) from JWT. |
| GET | `/auth/login/google` | No | Redirects to Google OIDC. |
| GET | `/auth/callback/google` | No | OAuth callback; exchanges code for tokens, creates or links user, redirects with app tokens. |

## Security

- **Passwords**: Argon2 via Passlib; only hashes are stored.
- **JWT**: RS256. Private key (PEM) used to sign access tokens; public key used by gateway and user-api (and auth-api for `/me`). Configure via `JWT_PRIVATE_KEY` / `JWT_PRIVATE_KEY_PATH` and `JWT_PUBLIC_KEY` / `JWT_PUBLIC_KEY_PATH`.
- **Refresh tokens**: Stored in DB (PostgreSQL `refresh_tokens` table); one per user, updated on each login. Used to issue new access tokens without re-entering password.

## Data Model (PostgreSQL)

- **users**: `username` (PK), `email`, `password` (hash).
- **federated**: `provider`, `subject_id` (PK), `user_id` — maps OIDC identity to app user.
- **refresh_tokens**: `user_id` (PK), `token`, `expires_at`, `revoked`.

When `AUTH_DB_URL` is not set or DB init fails, the auth repository uses an **in-memory** store (shared across requests in the same process) so that register/login tests work without a database.
