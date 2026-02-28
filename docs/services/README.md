# Services Documentation

High-level architecture and behavior of the main application services.

| Document | Description |
|----------|-------------|
| [authentication_architecture](authentication_architecture.md) | Auth-api, user-api, gateway; JWT (RS256), PostgreSQL, in-memory fallback, OIDC |
| [chat_memory_architecture](chat_memory_architecture.md) | Chat session persistence; Cassandra + in-memory fallback, data model, flow |
| [rag_and_ingestion](rag_and_ingestion.md) | RAG pipeline (Weaviate, rerankers, LLM), semantic cache (Redis), ingestion worker |

For API contracts and endpoints, see [API](../api/README.md). For data stores, see [DB](../db/README.md). For decisions, see [ADR](../adr/README.md).
