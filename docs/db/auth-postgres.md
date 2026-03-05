# Auth PostgreSQL

**Owner:** auth-api
**Purpose:** Persistent storage for user identity, federated (OIDC) mappings, and refresh tokens.
**Image:** `postgres:16`
**Port:** 5432
**Database name:** `auth_db`

---

## Connection

Configured via `AUTH_DB_URL`:

```
postgresql+psycopg2://auth_user:auth_pass@auth-db:5432/auth_db
```

| Component | Value | Description |
| --- | --- | --- |
| Driver | `psycopg2` | C-based PostgreSQL adapter for Python (via SQLAlchemy) |
| User | `auth_user` | Database role (configured in Docker Compose / K8s Secret) |
| Host | `auth-db` | Docker Compose service name or K8s Service DNS |
| Port | `5432` | Default PostgreSQL port |
| Database | `auth_db` | Dedicated database for auth-api |

**Fallback behavior:** If `AUTH_DB_URL` is empty or connection fails during `init_db()`, auth-api silently falls back to an in-memory store. This allows the app to run in:
- Local development without Docker Compose
- Unit tests without database fixtures
- Degraded mode if PostgreSQL is temporarily down at startup

---

## Schema (SQLAlchemy Declarative)

### users

```sql
CREATE TABLE users (
    username VARCHAR PRIMARY KEY,
    email    VARCHAR NOT NULL DEFAULT '',
    password VARCHAR NOT NULL DEFAULT ''
);
```

| Column | Type | Notes |
| --- | --- | --- |
| `username` | `VARCHAR` (PK) | Unique username, also used as JWT `sub` claim |
| `email` | `VARCHAR` | User email, can be empty for username-only accounts |
| `password` | `VARCHAR` | Argon2id hash (`$argon2id$v=19$m=65536,t=3,p=4$...`). Empty for OIDC-only users |

**SQLAlchemy model:**

```python
class UserModel(Base):
    __tablename__ = "users"
    username: Mapped[str] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(nullable=False, default="")
    password: Mapped[str] = mapped_column(nullable=False, default="")
```

### federated

```sql
CREATE TABLE federated (
    provider   VARCHAR NOT NULL,
    subject_id VARCHAR NOT NULL,
    user_id    VARCHAR NOT NULL,
    PRIMARY KEY (provider, subject_id)
);
```

| Column | Type | Notes |
| --- | --- | --- |
| `provider` | `VARCHAR` (PK part 1) | OIDC provider name: `"google"`, `"github"`, etc. |
| `subject_id` | `VARCHAR` (PK part 2) | Provider-assigned unique user ID |
| `user_id` | `VARCHAR` | FK to `users.username` (logical, not enforced) |

**Why composite PK?** A user can link multiple providers (Google + GitHub). The `(provider, subject_id)` pair uniquely identifies one external identity. Looking up by `user_id` finds all linked providers for a user.

### refresh_tokens

```sql
CREATE TABLE refresh_tokens (
    user_id    VARCHAR PRIMARY KEY,
    token      VARCHAR NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    revoked    BOOLEAN NOT NULL DEFAULT FALSE
);
```

| Column | Type | Notes |
| --- | --- | --- |
| `user_id` | `VARCHAR` (PK) | One refresh token per user (upserted on each login) |
| `token` | `VARCHAR` | JWT refresh token string |
| `expires_at` | `TIMESTAMP` | Expiration time (default: 7 days from login) |
| `revoked` | `BOOLEAN` | Set to `TRUE` on explicit logout or token rotation |

**Why one token per user?** Simpler than maintaining a list of active sessions. Each login replaces the previous refresh token. If you need multi-device support, change the PK to `(user_id, device_id)`.

---

## Entity Relationships

```mermaid
erDiagram
    users {
        varchar username PK
        varchar email
        varchar password
    }
    federated {
        varchar provider PK
        varchar subject_id PK
        varchar user_id FK
    }
    refresh_tokens {
        varchar user_id PK
        varchar token
        timestamp expires_at
        boolean revoked
    }

    users ||--o{ federated : "1:N (one user, many OIDC providers)"
    users ||--o| refresh_tokens : "1:1 (one refresh token per user)"
```

---

## Query Patterns

### Register a new user

```sql
INSERT INTO users (username, email, password) VALUES ('john_doe', 'john@example.com', '$argon2id$...');
```

### Login (find by username)

```sql
SELECT username, email, password FROM users WHERE username = 'john_doe';
-- Application verifies Argon2 hash in Python
```

### OIDC lookup (find by provider + subject)

```sql
SELECT user_id FROM federated WHERE provider = 'google' AND subject_id = '1234567890';
-- Then: SELECT * FROM users WHERE username = <user_id>;
```

### Save/update refresh token

```sql
-- Upsert pattern (INSERT or UPDATE)
INSERT INTO refresh_tokens (user_id, token, expires_at, revoked)
VALUES ('john_doe', 'eyJ...', '2025-03-08T12:00:00', FALSE)
ON CONFLICT (user_id)
DO UPDATE SET token = EXCLUDED.token, expires_at = EXCLUDED.expires_at, revoked = FALSE;
```

In the codebase this is done via SQLAlchemy's `session.get()` + update or `session.add()`.

---

## Schema Initialization

Tables are created automatically on startup:

```python
def init_db() -> bool:
    engine = create_engine(url, pool_pre_ping=True)
    Base.metadata.create_all(engine)    # CREATE TABLE IF NOT EXISTS for all models
    return True
```

`pool_pre_ping=True` enables a lightweight health check on each connection checkout from the pool, automatically recycling stale connections.

**No migration framework:** The current setup uses `create_all()` which only creates missing tables — it does not alter existing tables. For production schema evolution, add Alembic:

```bash
alembic init migrations
alembic revision --autogenerate -m "add avatar column"
alembic upgrade head
```

---

## Connection Pooling

SQLAlchemy's default connection pool:

| Parameter | Default | Description |
| --- | --- | --- |
| `pool_size` | 5 | Persistent connections held open |
| `max_overflow` | 10 | Additional connections created under load (total max: 15) |
| `pool_recycle` | -1 (disabled) | Close connections after N seconds (set to 1800 for long-lived apps) |
| `pool_pre_ping` | `True` (set in code) | Test connection before use to avoid stale connections |

For Kubernetes with 2 replicas × 5 pool size = 10 concurrent connections to PostgreSQL. PostgreSQL's default `max_connections` is 100, so this is well within limits.

---

## In-Memory Fallback (Detail)

When DB is unavailable, `PostgreAuthRepository` uses class-level shared dictionaries:

```python
class PostgreAuthRepository:
    _memory_users: Dict[str, User] = {}               # shared across all instances
    _memory_federated: Dict[Tuple[str, str], str] = {} # shared across all instances

    def _use_db(self) -> bool:
        return bool(is_db_available())
```

Every method checks `_use_db()` first. If False, it operates on the class-level dicts. Because they are **class-level** (not instance-level), all injected instances within the same process see the same data. This is important because FastAPI creates a new `PostgreAuthRepository` per request via `Depends()`.

**Limitations:**
- Data is lost on process restart
- Not shared across multiple auth-api processes (Kubernetes pods)
- No refresh token tracking (in-memory save is a no-op)

---

## Backup and Recovery

### Docker Compose (local development)

```bash
# Backup
docker exec auth-db pg_dump -U auth_user auth_db > auth_backup.sql

# Restore
docker exec -i auth-db psql -U auth_user auth_db < auth_backup.sql
```

### Kubernetes (production)

```bash
# Backup
kubectl exec auth-db-0 -n rag-us-law -- pg_dump -U auth_user auth_db > auth_backup.sql

# Restore
kubectl exec -i auth-db-0 -n rag-us-law -- psql -U auth_user auth_db < auth_backup.sql
```

For automated backups, consider a CronJob that runs `pg_dump` to S3 daily, or use AWS RDS PostgreSQL instead of self-managed for automatic backups, point-in-time recovery, and multi-AZ failover.
