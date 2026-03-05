# User MongoDB

**Owner:** user-api
**Purpose:** Document store for user profiles (display name, bio, avatar URL, and other non-security attributes).
**Image:** `mongo:7`
**Port:** 27017
**Database:** `user_db` (from connection string)

---

## Connection

Configured via `USER_DB_URL`:

```
mongodb://user-db:27017/user_db
```

The `MongoClient` is initialized at module import time in `src/service/profile_service.py`:

```python
client = MongoClient(settings.USER_DB_URL)
db = client.get_default_database()        # "user_db" from the connection string
profiles = db["user_profiles"]
```

`get_default_database()` extracts the database name from the URL path (`/user_db`). The client manages its own connection pool internally (default pool size: 100 connections, max: 100).

---

## Collection: `user_profiles`

### Document Shape

```json
{
  "_id": "ObjectId('65e1a2b3c4d5e6f7a8b9c0d1')",
  "user_id": "john_doe",
  "display_name": "John Doe",
  "bio": "Legal researcher specializing in constitutional law",
  "avatar_url": "https://example.com/avatars/john.jpg"
}
```

| Field | Type | Description |
| --- | --- | --- |
| `_id` | `ObjectId` | Auto-generated MongoDB document ID |
| `user_id` | `string` | Matches JWT `sub` claim from auth-api. This is the logical primary key. |
| `display_name` | `string` or `null` | User's chosen display name |
| `bio` | `string` or `null` | Short biography or description |
| `avatar_url` | `string` or `null` | URL to profile picture |

---

## Query Patterns

### Read profile

```javascript
db.user_profiles.findOne({ "user_id": "john_doe" })
```

Returns the full document or `null` if no profile exists. When `null`, user-api returns a default profile with `null` fields:

```python
doc = profiles.find_one({"user_id": user_id}) or {"user_id": user_id}
return UserProfile(**doc)
```

### Upsert profile

```javascript
db.user_profiles.updateOne(
  { "user_id": "john_doe" },
  { "$set": {
      "user_id": "john_doe",
      "display_name": "John Doe",
      "bio": "Updated bio",
      "avatar_url": "https://..."
    }
  },
  { "upsert": true }
)
```

`upsert: true` means:
- If a document with `user_id: "john_doe"` exists → update it (`$set` replaces specified fields)
- If no document exists → insert a new one with the `$set` fields

This is the only write operation. There is no explicit create endpoint — the first PUT creates the profile.

---

## Indexing

### Recommended production index

```javascript
db.user_profiles.createIndex({ "user_id": 1 }, { unique: true })
```

**Why unique index?**
- Without it, MongoDB scans the entire collection on every `findOne({ "user_id": ... })` — O(n) per request
- With the index, lookups are O(log n) via B-tree
- The `unique` constraint prevents duplicate profiles (defense in depth — the application already prevents this via upsert)

**Current state:** The codebase does not create this index programmatically. For production, create it manually or add an initialization step:

```python
profiles.create_index("user_id", unique=True)
```

---

## Why MongoDB (Not PostgreSQL)

| Factor | MongoDB | PostgreSQL |
| --- | --- | --- |
| Schema | Flexible — add fields without ALTER TABLE | Rigid — requires migration |
| Profile data | Naturally a JSON document | Requires column definitions |
| Joins | Not needed — profiles are self-contained | Would be unused |
| Scaling | Easy horizontal sharding by `user_id` | Requires pgBouncer / Citus for sharding |
| Transactions | Not needed — single-document operations | Overkill for CRUD |

The profile service does exactly two operations: `findOne` and `updateOne`. MongoDB excels at this pattern. PostgreSQL's relational strengths (joins, transactions, constraints) are unnecessary here.

---

## Data Lifecycle

```
User registers via auth-api
  → user record created in PostgreSQL (username, email, password hash)
  → NO profile created in MongoDB yet

User visits profile page
  → GET /profiles/me
  → MongoDB findOne returns null → user-api returns default empty profile

User updates profile
  → PUT /profiles/me with display_name, bio
  → MongoDB upsert creates the document

Subsequent reads
  → findOne returns the stored profile
```

**No cascade delete:** If a user is deleted from auth-api's PostgreSQL, the MongoDB profile is orphaned. For production, implement a cleanup job or event-driven deletion (auth-api publishes `UserDeleted` event → user-api listens and deletes the profile).

---

## Backup and Recovery

### Docker Compose

```bash
# Backup
docker exec user-db mongodump --archive=/tmp/user_db.archive --db=user_db
docker cp user-db:/tmp/user_db.archive ./user_db_backup.archive

# Restore
docker cp ./user_db_backup.archive user-db:/tmp/user_db.archive
docker exec user-db mongorestore --archive=/tmp/user_db.archive --drop
```

### Kubernetes

```bash
# Backup
kubectl exec user-db-0 -n rag-us-law -- mongodump --archive=/tmp/backup.archive --db=user_db
kubectl cp rag-us-law/user-db-0:/tmp/backup.archive ./user_db_backup.archive

# Restore
kubectl cp ./user_db_backup.archive rag-us-law/user-db-0:/tmp/backup.archive
kubectl exec user-db-0 -n rag-us-law -- mongorestore --archive=/tmp/backup.archive --drop
```

For production, consider MongoDB Atlas (managed) or schedule CronJob backups to S3.

---

## Performance Characteristics

| Operation | Complexity (with index) | Latency |
| --- | --- | --- |
| `findOne` by `user_id` | O(log n) | < 1ms |
| `updateOne` by `user_id` | O(log n) | < 1ms |
| Full collection scan (no index) | O(n) | Grows with user count |

With 100K users, the `user_profiles` collection is approximately 50 MB (500 bytes average per document). MongoDB caches this entirely in the WiredTiger cache (default: 50% of RAM), so reads are served from memory.
