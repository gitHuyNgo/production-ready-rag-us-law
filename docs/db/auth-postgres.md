# Auth PostgreSQL

**Owner**: auth-api  
**Purpose**: Persistent storage for user identity, federated (OIDC) mappings, and refresh tokens.

## Connection

- Configured via `AUTH_DB_URL` (e.g. `postgresql+psycopg2://user:pass@host:5432/dbname`).
- If unset or connection fails, auth-api uses an **in-memory** store (shared across repo instances in the same process) so that register/login still work (e.g. tests, minimal dev).

## Schema (SQLAlchemy)

- **users**  
  - `username` (PK), `email`, `password` (hashed).

- **federated**  
  - `provider` (PK), `subject_id` (PK), `user_id` — links OIDC provider + subject to app user.

- **refresh_tokens**  
  - `user_id` (PK), `token`, `expires_at`, `revoked` — one row per user; updated on each login.

Tables are created on startup via `Base.metadata.create_all(engine)` in `init_db()` (`app/auth-api/src/db.py`). Repository layer is in `src/repositories/postgres_auth_repo.py`; it uses `get_db_session()` context manager (commit on success, rollback on exception).
