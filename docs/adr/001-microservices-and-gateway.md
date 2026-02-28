# ADR 001: Microservices and API Gateway

## Status

Accepted.

## Context

The system must support authentication, user profiles, and a RAG-based chat service. A single monolith would couple security, profile data, and LLM/vector workloads and complicate scaling and deployment.

## Decision

- **API Gateway** (`api-gateway`): Single entry point for clients. Handles CORS, rate limiting (SlowAPI), and JWT verification. Proxies HTTP and WebSocket traffic to internal services. No business logic; forwards requests to auth-api, user-api, and chat-api with optional `X-User-Id` from the validated token.
- **Auth API** (`auth-api`): Identity, credentials, JWT issuance (RS256), refresh tokens, and OIDC (e.g. Google). Uses PostgreSQL (or in-memory fallback when DB is unavailable).
- **User API** (`user-api`): Profile CRUD (display name, bio, etc.). Uses MongoDB. Validates JWT with auth-api’s public key; does not store passwords.
- **Chat API** (`chat-api`): RAG pipeline (Weaviate retrieval, BM25 + Cohere rerank, OpenAI LLM), semantic cache (Redis), and chat memory (Cassandra or in-memory).
- **Ingestion Worker** (`ingestion-worker`): Batch ingestion of PDFs into Weaviate and flush of RAG semantic cache after ingest. No HTTP server; CLI/script.

Frontend and external clients talk only to the gateway; internal services are not exposed directly.

## Consequences

- Clear separation of concerns and independent scaling.
- Gateway is a single point of failure and must be robust (rate limiting, auth, proxy correctness).
- Operational complexity: multiple services, env and key configuration (e.g. JWT public key on gateway and user-api).
