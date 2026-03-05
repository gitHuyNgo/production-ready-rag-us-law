# Authentication & User Management Architecture

This document describes the complete authentication and user management system — how users register, log in, access protected resources, and manage their profiles across three cooperating services.

---

## Service Map

```mermaid
graph TD
    C["CLIENT<br/>Browser / Mobile / API consumer<br/>Knows: API Gateway URL, Bearer token format<br/>Stores: access_token (memory), refresh_token (httponly cookie)"]

    GW["API GATEWAY :8080<br/>1. CORS (allow frontend origin)<br/>2. Rate limiting (SlowAPI: 100/min default, 20/min for auth)<br/>3. JWT verification (RS256 with auth-api public key)<br/>4. Route to backend service<br/>5. Add X-User-Id header from JWT sub claim<br/><br/>Public routes: /auth/register, /auth/token, /health, /docs<br/>Protected routes: /auth/me, /profiles/*, /chat/*"]

    AUTH["auth-api :8001<br/>PostgreSQL (auth-db)"]
    USER["user-api :8002<br/>MongoDB (user-db)"]
    CHAT["chat-api :8000<br/>Weaviate / Redis / Cassandra"]

    C -- "HTTPS" --> GW
    GW --> AUTH
    GW --> USER
    GW --> CHAT
```

---

## Flow 1: Registration

```mermaid
sequenceDiagram
    participant C as Client
    participant G as Gateway
    participant A as auth-api
    participant PG as PostgreSQL

    C->>G: POST /auth/register {username, email, pw}
    Note over G: public route — no JWT check
    G->>A: POST /auth/register
    Note over A: AuthService.register()<br/>hash password (Argon2id)<br/>pwd_context.hash(pw) → "$argon2id$v=19$..."
    A->>PG: INSERT INTO users (username, email, hash)
    Note over A: (optional) publish UserCreated event
    A-->>G: 201 {username, email}
    G-->>C: 201 {username, email}
```

### Password Hashing Details

| Property | Value |
| --- | --- |
| Algorithm | Argon2id |
| Memory cost | 65536 KB (64 MB) |
| Time cost | 3 iterations |
| Parallelism | 4 lanes |
| Salt | 16 bytes (auto-generated per hash) |
| Output hash | 32 bytes (base64-encoded in stored string) |

Argon2id is the recommended algorithm per OWASP. It is resistant to both GPU attacks (memory-hard) and side-channel attacks (data-independent memory access pattern in the id variant).

---

## Flow 2: Login (Token Issuance)

```mermaid
sequenceDiagram
    participant C as Client
    participant G as Gateway
    participant A as auth-api
    participant PG as PostgreSQL

    C->>G: POST /auth/token (form: username, pw)
    Note over G: public route — no JWT check
    G->>A: POST /auth/token
    A->>PG: SELECT FROM users WHERE username=...
    PG-->>A: User row
    Note over A: pwd_context.verify(pw, hash) → True (constant-time)
    Note over A: Create access token (JWT RS256)<br/>payload: {sub: username, exp: now+30min}<br/>signed with PRIVATE key
    Note over A: Create refresh token (JWT RS256)<br/>payload: {sub: username, exp: now+7days, type: refresh}
    A->>PG: UPSERT refresh_tokens
    A-->>G: 200 {access_token, refresh_token}<br/>Set-Cookie: refresh_token
    G-->>C: 200 {access_token, refresh_token}<br/>Set-Cookie: refresh_token
```

### Token Anatomy

**Access Token (30-minute lifetime):**

| Part | Value |
| --- | --- |
| Header | `{ "alg": "RS256", "typ": "JWT" }` |
| Payload | `{ "sub": "john_doe", "exp": 1709712000, "iat": 1709710200 }` |
| Signature | `RSA_SHA256(header.payload, PRIVATE_KEY)` |

**Refresh Token (7-day lifetime):**

| Part | Value |
| --- | --- |
| Header | `{ "alg": "RS256", "typ": "JWT" }` |
| Payload | `{ "sub": "john_doe", "exp": 1710316800, "iat": 1709710200, "type": "refresh" }` |
| Signature | `RSA_SHA256(header.payload, PRIVATE_KEY)` |

---

## Flow 3: Accessing a Protected Resource

```mermaid
sequenceDiagram
    participant C as Client
    participant G as Gateway
    participant U as user-api
    participant MG as MongoDB

    C->>G: GET /profiles/me<br/>Authorization: Bearer access_token
    Note over G: 1. Extract Bearer token<br/>2. jwt.decode(token, PUBLIC_KEY, RS256)<br/>3. check exp > now → extract sub = "john_doe"<br/>4. Add X-User-Id: john_doe header
    G->>U: GET /profiles/me<br/>Authorization: Bearer token<br/>X-User-Id: john_doe
    Note over U: Decode JWT AGAIN with public key<br/>(does NOT trust X-User-Id blindly)<br/>→ sub = "john_doe"
    U->>MG: findOne({user_id: "john_doe"})
    MG-->>U: profile doc
    U-->>G: 200 {user_id, display_name, bio, ...}
    G-->>C: 200 {user_id, display_name, bio, ...}
```

### Why Double JWT Verification?

Both the gateway and user-api verify the JWT independently. This is **defense in depth**:

- If the gateway has a bug that skips JWT verification for certain paths, user-api still rejects unauthenticated requests
- user-api can be deployed behind a different gateway in the future without losing security
- The cost is negligible — RS256 verify is a single RSA public key operation (~0.1ms)

---

## Flow 4: Google OIDC Login

```mermaid
sequenceDiagram
    participant B as Browser
    participant G as Gateway
    participant A as auth-api
    participant GOOG as Google
    participant PG as PostgreSQL

    B->>G: GET /auth/login/google
    G->>A: proxy
    A-->>B: 302 → Google consent screen
    Note over B: User authorizes on Google
    B->>G: GET /auth/callback/google?code=XYZ
    G->>A: proxy
    A->>GOOG: exchange code for tokens
    GOOG-->>A: id_token
    Note over A: decode id_token → sub, email
    A->>PG: get_by_federated("google", sub)
    PG-->>A: existing user or None
    alt new user
        A->>PG: INSERT users + federated
    end
    Note over A: create access_token + refresh_token
    A-->>B: 302 → frontend with tokens
```

---

## RS256 Key Distribution

```mermaid
graph TD
    AA["auth-api<br/>PRIVATE KEY (signs) — most sensitive secret; compromise = forgeable JWTs<br/>PUBLIC KEY (verifies)<br/>Loaded from JWT_PRIVATE_KEY_PATH → /run/secrets/auth_private.pem<br/>and JWT_PUBLIC_KEY_PATH → /run/secrets/auth_public.pem"]
    GW["gateway<br/>PUBLIC KEY only<br/>Can: verify<br/>Cannot: sign"]
    UA["user-api<br/>PUBLIC KEY only<br/>Can: verify<br/>Cannot: sign"]

    AA -- "public key shared with" --> GW
    AA -- "public key shared with" --> UA
```

### Key Rotation Procedure

1. Generate new RSA key pair: `openssl genrsa -out private_new.pem 2048 && openssl rsa -in private_new.pem -pubout -out public_new.pem`
2. Deploy the new **public key** to gateway and user-api first (they now accept tokens signed by either old or new key)
3. Deploy the new **private key** to auth-api (new tokens are signed with new key)
4. Wait for all old tokens to expire (30 minutes for access tokens)
5. Remove the old public key from gateway and user-api

Step 2 before step 3 ensures there is no window where newly issued tokens are rejected.

---

## Configuration Reference

### auth-api

| Variable | Default | Description |
| --- | --- | --- |
| `AUTH_DB_URL` | (empty) | PostgreSQL connection string |
| `JWT_PRIVATE_KEY_PATH` | (empty) | Path to RS256 private key PEM |
| `JWT_PUBLIC_KEY_PATH` | (empty) | Path to RS256 public key PEM |
| `JWT_ALGORITHM` | `RS256` | Signing algorithm |
| `SESSION_SECRET_KEY` | (required) | Starlette session secret (for OIDC state) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |
| `GOOGLE_CLIENT_ID` | (empty) | Google OIDC |
| `GOOGLE_CLIENT_SECRET` | (empty) | Google OIDC |
| `GOOGLE_REDIRECT_URI` | (empty) | Google OIDC callback URL |

### api-gateway

| Variable | Default | Description |
| --- | --- | --- |
| `JWT_PUBLIC_KEY_PATH` | (empty) | Path to RS256 public key PEM |
| `JWT_ALGORITHM` | `RS256` | Verification algorithm |
| `AUTH_API_URL` | `http://auth-api:8001` | Upstream auth-api |
| `USER_API_URL` | `http://user-api:8002` | Upstream user-api |
| `CHAT_API_URL` | `http://chat-api:8000` | Upstream chat-api |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed origins |
| `RATE_LIMIT_DEFAULT` | `100/minute` | Rate limit for most routes |

### user-api

| Variable | Default | Description |
| --- | --- | --- |
| `JWT_PUBLIC_KEY_PATH` | (empty) | Path to RS256 public key PEM |
| `JWT_ALGORITHM` | `RS256` | Verification algorithm |
| `USER_DB_URL` | `mongodb://user-db:27017/user_db` | MongoDB connection |

---

## Security Checklist

| Check | Status | Notes |
| --- | --- | --- |
| Passwords hashed with Argon2id | Done | Via Passlib CryptContext |
| JWT signed with RS256 (asymmetric) | Done | Private key only on auth-api |
| Refresh tokens stored server-side | Done | PostgreSQL `refresh_tokens` table |
| Refresh token in httponly cookie | Done | JS cannot access |
| CORS restricted | Done | Only `localhost:3000` by default |
| Rate limiting | Done | SlowAPI on gateway |
| OIDC state validated | Done | Starlette SessionMiddleware |
| Public key only on verifiers | Done | Gateway + user-api have no private key |
| Token expiration checked | Done | `exp` claim verified by jose |
