# Database and Data Stores

The system uses several data stores, each owned by specific services.

| Store | Service(s) | Purpose |
|-------|------------|---------|
| [PostgreSQL (auth)](auth-postgres.md) | auth-api | Users, federated identities, refresh tokens |
| [MongoDB](user-mongodb.md) | user-api | User profiles (display name, bio, etc.) |
| [Weaviate](weaviate.md) | chat-api, ingestion-worker | Vector store for RAG document chunks |
| [Redis](redis-semantic-cache.md) | chat-api, ingestion-worker | Semantic cache for RAG responses |
| [Cassandra](cassandra-chat-memory.md) | chat-api | Chat session message history (optional) |

All stores are optional or have fallbacks where noted (e.g. auth in-memory when DB URL is unset; chat memory in-memory when Cassandra is unavailable).
