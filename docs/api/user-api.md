# User API

The User API manages non-security user profile data (display name, bio, avatar). It is exposed via the gateway at `/profiles/*`. All endpoints require a valid JWT from the Auth API.

**Source code:** `app/user-api/`
**Port:** 8002
**Framework:** FastAPI
**Router:** `src/routers/profile_router.py`
**Data store:** MongoDB

---

## Endpoints

### GET `/profiles/me`

Retrieve the current user's profile.

**Auth:** Bearer token (required)

**Request headers:**

```
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
```

**Response (200) — profile exists:**

```json
{
  "user_id": "john_doe",
  "display_name": "John Doe",
  "bio": "Legal researcher specializing in constitutional law",
  "avatar_url": "https://example.com/avatars/john.jpg"
}
```

**Response (200) — no profile yet (returns empty shell):**

```json
{
  "user_id": "john_doe",
  "display_name": null,
  "bio": null,
  "avatar_url": null
}
```

**Errors:**

| Status | Detail | Cause |
| --- | --- | --- |
| 401 | `Could not validate credentials` | Missing, expired, or invalid JWT |

**Internal flow:**

```
Client → Gateway (/profiles/me, protected route)
  → Gateway: verify JWT with RS256 public key → extract sub
  → Gateway: add X-User-Id header
  → Forward to user-api GET /profiles/me
    → get_current_user_id(): decode JWT again with public key → sub
    → get_profile(user_id)
      → MongoDB: db.user_profiles.find_one({"user_id": sub})
      → if not found: return UserProfile(user_id=sub) with null fields
      → if found: return UserProfile(**doc)
    → return UserProfileDto
```

---

### PUT `/profiles/me`

Create or update the current user's profile. The `user_id` in the request body is ignored — the server always uses the `sub` claim from the JWT.

**Auth:** Bearer token (required)

**Request:**

```json
{
  "user_id": "ignored_value",
  "display_name": "John Doe",
  "bio": "Updated bio text",
  "avatar_url": "https://example.com/avatars/john_v2.jpg"
}
```

**Response (200):**

```json
{
  "user_id": "john_doe",
  "display_name": "John Doe",
  "bio": "Updated bio text",
  "avatar_url": "https://example.com/avatars/john_v2.jpg"
}
```

**Errors:**

| Status | Detail | Cause |
| --- | --- | --- |
| 401 | `Could not validate credentials` | Missing, expired, or invalid JWT |
| 422 | Validation error | Request body does not match `UserProfileDto` schema |

**Internal flow:**

```
Client → Gateway (/profiles/me, protected route)
  → Gateway: verify JWT → extract sub → add X-User-Id header
  → Forward to user-api PUT /profiles/me
    → get_current_user_id(): decode JWT → sub = "john_doe"
    → upsert_profile(user_id, profile)
      → data = profile.model_dump()
      → data["user_id"] = user_id     ← override with JWT sub
      → MongoDB: db.user_profiles.update_one(
          {"user_id": user_id},
          {"$set": data},
          upsert=True                  ← create if not exists
        )
    → return UserProfileDto
```

---

## Authentication Flow (JWT Verification)

User-api verifies tokens independently — no call to auth-api per request:

```python
def get_current_user_id(token: str) -> str:
    public_key = get_jwt_public_key()      # same RS256 public key as auth-api
    payload = jwt.decode(token, public_key, algorithms=["RS256"])
    sub = payload.get("sub")               # username from auth-api
    return sub
```

```mermaid
flowchart LR
    C["Client<br/>Bearer token"]
    G["api-gateway<br/>verify JWT with pubkey<br/>add X-User-Id header"]
    U["user-api<br/>verify JWT with same pubkey"]

    C --> G --> U
```

Both gateway and user-api verify independently. The gateway adds `X-User-Id` for convenience, but user-api does not trust it blindly — it re-verifies the JWT itself.

---

## Data Model (MongoDB)

### Collection: `user_profiles`

```json
{
  "_id": "ObjectId(...)",
  "user_id": "john_doe",
  "display_name": "John Doe",
  "bio": "Legal researcher specializing in constitutional law",
  "avatar_url": "https://example.com/avatars/john.jpg"
}
```

**Index:** `user_id` is used as the lookup key in `find_one()` and `update_one()`. For production, create a unique index:

```javascript
db.user_profiles.createIndex({ "user_id": 1 }, { unique: true })
```

**Why MongoDB for profiles?**
- Schema flexibility — profile fields can be added without migrations
- Document model maps naturally to the JSON profile object
- No joins needed — each profile is a self-contained document
- user-api is the only service that reads/writes profiles — no shared access concerns

---

## Domain Models

### UserProfile (domain)

```python
class UserProfile(BaseModel):
    user_id: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
```

### UserProfileDto (API)

```python
class UserProfileDto(BaseModel):
    user_id: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
```

The domain model and DTO are currently identical. They are kept separate so the DTO can diverge later (e.g., adding `created_at` to the domain model without exposing it in the API).

---

## Service Layer

```python
# src/service/profile_service.py
client = MongoClient(settings.USER_DB_URL)   # connects on import
db = client.get_default_database()
profiles = db["user_profiles"]

def get_profile(user_id: str) -> UserProfile:
    doc = profiles.find_one({"user_id": user_id}) or {"user_id": user_id}
    return UserProfile(**doc)

def upsert_profile(user_id: str, profile: UserProfile) -> UserProfile:
    data = profile.model_dump()
    data["user_id"] = user_id
    profiles.update_one({"user_id": user_id}, {"$set": data}, upsert=True)
    return UserProfile(**data)
```

The MongoDB client is initialized at module import time. The `get_default_database()` call uses the database name from the connection string (e.g., `mongodb://user-db:27017/user_db` → database `user_db`).

---

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `USER_DB_URL` | `mongodb://user-db:27017/user_db` | MongoDB connection string (includes database name) |
| `JWT_ALGORITHM` | `RS256` | JWT verification algorithm |
| `JWT_PUBLIC_KEY` | (empty) | PEM public key as string |
| `JWT_PUBLIC_KEY_PATH` | (empty) | Path to PEM public key file |

---

## Relationship to Other Services

```
auth-api                    user-api                   MongoDB
─────────                   ────────                   ───────
Creates user account  →     user-api does NOT           Stores only profiles
Issues JWT with sub   →     know about passwords        keyed by user_id
                            Verifies JWT independently
                            Uses sub as profile key
```

- **auth-api** owns identity (username, password, tokens)
- **user-api** owns profile (display_name, bio, avatar_url)
- They share only the `user_id` (JWT `sub`) as a foreign key
- user-api never calls auth-api at runtime — the shared public key is enough
