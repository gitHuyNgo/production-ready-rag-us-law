# Auth API

The Auth API handles identity, credentials, and token lifecycle. It is exposed via the gateway at `/auth/*`.

**Source code:** `app/auth-api/`
**Port:** 8001
**Framework:** FastAPI
**Router:** `src/routers/auth_router.py`, `src/routers/google_router.py`

---

## Endpoints

### POST `/auth/register`

Create a new user account with username, email, and password.

**Auth:** None

**Request:**

```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecureP@ss123"
}
```

**Response (201):**

```json
{
  "username": "john_doe",
  "email": "john@example.com"
}
```

**Errors:**

| Status | Detail | Cause |
| --- | --- | --- |
| 409 | `Username already registered` | Username exists in DB or in-memory store |
| 422 | Validation error | Missing or invalid field (Pydantic) |

**Internal flow:**

```
Client → Gateway (/auth/register, public route, no JWT check)
  → auth-api POST /auth/register
    → AuthService.register()
      → hash password with Argon2 (Passlib)
      → PostgreAuthRepository.create_user()
        → if DB available: INSERT INTO users (username, email, password)
        → if DB unavailable: store in shared _memory_users dict
      → (optional) publish UserCreated event via publisher
    → return UserOut(username, email)
```

---

### POST `/auth/token`

Login with credentials. Returns access and refresh tokens.

**Auth:** None
**Content-Type:** `application/x-www-form-urlencoded` (OAuth2 password flow)

**Request (form body):**

```
username=john_doe&password=SecureP@ss123
```

**Response (200):**

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "bearer"
}
```

**Additionally:** Sets an `httponly` cookie named `refresh_token` with `samesite=lax`.

**Cookie details:**

| Attribute | Value |
| --- | --- |
| `key` | `refresh_token` |
| `httponly` | `true` (JavaScript cannot read it) |
| `samesite` | `lax` |
| `secure` | `false` (set to `true` for HTTPS in prod) |
| `max_age` | `REFRESH_TOKEN_EXPIRE_DAYS * 86400` seconds |
| `path` | `/` |

**Errors:**

| Status | Detail | Cause |
| --- | --- | --- |
| 401 | `Incorrect username or password` | No user found or Argon2 verify fails |

**Internal flow:**

```
Client → Gateway (/auth/token, public route)
  → auth-api POST /auth/token
    → AuthService.login(username, password)
      → repo.get_by_username(username) → User or None
      → if None: raise 401
      → passlib.verify(password, user.password) → bool
      → if False: raise 401
      → create access_token: JWT signed with RS256 private key
        payload: { "sub": username, "exp": now + 30min }
      → create refresh_token: JWT signed with RS256 private key
        payload: { "sub": username, "exp": now + 7days, "type": "refresh" }
      → repo.save_refresh_token(username, refresh_token, expires_at)
        → if DB: INSERT/UPDATE refresh_tokens table
      → return Token(access_token, refresh_token, "bearer")
    → set refresh_token cookie on Response
```

---

### GET `/auth/me`

Get the current authenticated user's identity.

**Auth:** Bearer token (access_token)

**Request headers:**

```
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
```

**Response (200):**

```json
{
  "username": "john_doe",
  "email": "john@example.com"
}
```

**Errors:**

| Status | Detail | Cause |
| --- | --- | --- |
| 401 | `Could not validate credentials` | Missing, expired, or invalid JWT |

**Internal flow:**

```
Client → Gateway (/auth/me, protected route)
  → Gateway: verify JWT with public key → extract sub
  → Forward to auth-api with X-User-Id header
  → auth-api GET /auth/me
    → AuthService.get_current_user_from_token(token)
      → decode JWT with public key → payload["sub"]
      → repo.get_by_username(sub) → User
      → return UserOut(username, email)
```

---

### GET `/auth/login/google`

Initiate Google OIDC login. Redirects the browser to Google's consent screen.

**Auth:** None

**Response:** HTTP 302 redirect to `https://accounts.google.com/o/oauth2/v2/auth?...`

**Required config:** `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` must be set. Initialized in `src/core/external/google.py` during app lifespan.

---

### GET `/auth/callback/google`

Google OIDC callback. Exchanges the authorization code for tokens, finds or creates a user, and redirects with application tokens.

**Auth:** None (called by Google after consent)

**Query params:**

| Param | Description |
| --- | --- |
| `code` | Authorization code from Google |
| `state` | CSRF state token |

**Internal flow:**

```
Google redirects user to /auth/callback/google?code=XYZ&state=ABC
  → auth-api receives callback
    → exchange code for Google tokens (id_token, access_token)
    → decode id_token → extract sub (Google user ID), email
    → repo.get_by_federated("google", sub)
      → if user exists: return existing User
      → if not: repo.create_federated_user("google", sub, email_as_username, email)
    → create app access_token + refresh_token (same as /auth/token)
    → redirect to frontend with tokens as query params or cookies
```

---

## Security Deep Dive

### Password Hashing

```python
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
```

- **Algorithm:** Argon2id (winner of the Password Hashing Competition)
- **Why not bcrypt?** Argon2 is resistant to GPU and ASIC attacks because it requires significant memory (not just CPU)
- **Hash format stored in DB:** `$argon2id$v=19$m=65536,t=3,p=4$...` (includes salt, parameters, and hash)
- **Verification:** `pwd_context.verify(plain_password, hashed_password)` — constant-time comparison

### JWT Token Structure

**Access token payload (decoded):**

```json
{
  "sub": "john_doe",
  "exp": 1709712000,
  "iat": 1709710200
}
```

**Signing process:**

```
Header:    {"alg": "RS256", "typ": "JWT"}
Payload:   {"sub": "john_doe", "exp": ..., "iat": ...}
Signature: RSA_SHA256(base64(header) + "." + base64(payload), PRIVATE_KEY)
```

**Verification by gateway/user-api:**

```
Receive token → split into header.payload.signature
→ RSA_SHA256_VERIFY(header.payload, signature, PUBLIC_KEY) → valid?
→ Check exp > now → not expired?
→ Extract sub → user identity
```

### Key Distribution

```mermaid
graph TD
    AA["auth-api<br/>PRIVATE key — signs tokens<br/>PUBLIC key — verifies own tokens /me"]
    GW["api-gateway<br/>PUBLIC key only (read-only)<br/>verifies all requests"]
    UA["user-api<br/>PUBLIC key only (read-only)<br/>verifies /profiles/*"]

    AA -- "public key distributed to" --> GW
    AA -- "public key distributed to" --> UA
```

The private key never leaves auth-api. If the gateway or user-api is compromised, the attacker can only verify tokens, not forge them.

---

## Data Model (PostgreSQL)

### users table

```sql
CREATE TABLE users (
    username VARCHAR PRIMARY KEY,
    email    VARCHAR NOT NULL DEFAULT '',
    password VARCHAR NOT NULL DEFAULT ''    -- Argon2 hash, empty for OIDC-only users
);
```

### federated table

```sql
CREATE TABLE federated (
    provider   VARCHAR NOT NULL,              -- 'google', 'github', etc.
    subject_id VARCHAR NOT NULL,              -- unique ID from the provider
    user_id    VARCHAR NOT NULL,              -- FK → users.username
    PRIMARY KEY (provider, subject_id)
);
```

### refresh_tokens table

```sql
CREATE TABLE refresh_tokens (
    user_id    VARCHAR PRIMARY KEY,           -- one refresh token per user
    token      VARCHAR NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    revoked    BOOLEAN NOT NULL DEFAULT FALSE
);
```

### Entity Relationship

```mermaid
erDiagram
    users ||--o{ federated : "1:N — one user can have multiple OIDC providers"
    users ||--o| refresh_tokens : "1:1 — one refresh token per user, upserted on login"
```

---

## In-Memory Fallback

When `AUTH_DB_URL` is not set or database connection fails on startup:

```python
# PostgreAuthRepository uses class-level dicts shared across all instances
_memory_users: Dict[str, User] = {}
_memory_federated: Dict[Tuple[str, str], str] = {}
```

This allows auth-api to run without a database for:
- Local development without Docker Compose
- Unit tests without database fixtures
- Graceful degradation if PostgreSQL is temporarily unavailable at startup

**Limitations:** Data is lost on process restart. Not shared across multiple auth-api instances (each process has its own memory).

---

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `AUTH_DB_URL` | (empty) | PostgreSQL connection string. Empty = in-memory mode |
| `JWT_ALGORITHM` | `RS256` | JWT signing algorithm |
| `JWT_PRIVATE_KEY` | (empty) | PEM private key as string (newlines as `\n`) |
| `JWT_PRIVATE_KEY_PATH` | (empty) | Path to PEM private key file (takes precedence) |
| `JWT_PUBLIC_KEY` | (empty) | PEM public key as string |
| `JWT_PUBLIC_KEY_PATH` | (empty) | Path to PEM public key file |
| `SESSION_SECRET_KEY` | (required) | Secret for Starlette session middleware (OIDC state) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |
| `GOOGLE_CLIENT_ID` | (empty) | Google OIDC client ID |
| `GOOGLE_CLIENT_SECRET` | (empty) | Google OIDC client secret |
| `GOOGLE_REDIRECT_URI` | (empty) | Google OIDC callback URL |

---

## Startup Sequence

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_google()                      # 1. Configure OIDC provider
    events_module.publisher = get_publisher()  # 2. Init event publisher (Kafka or no-op)
    if init_db():                      # 3. Try PostgreSQL connection
        app.state.db_available = True  #    → create engine, create tables
    else:
        app.state.db_available = False #    → fall back to in-memory
    yield
    if hasattr(publisher, "close"):
        await publisher.close()        # 4. Cleanup on shutdown
```
