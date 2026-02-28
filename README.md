# Production-Ready RAG for US Law

End-to-end deployment of a scalable RAG pipeline for U.S. legal Q&A: microservices, vector retrieval, semantic cache, chat memory, authentication, and CI/CD.

## Overview

The system is organized as a **microservices** stack behind a single **API Gateway**:

| Component | Description |
|-----------|-------------|
| **`api-gateway`** | Single entry point: CORS, rate limiting, JWT verification, HTTP/WebSocket proxy to backend services. |
| **`auth-api`** | Identity, credentials, JWT (RS256), refresh tokens, OIDC (e.g. Google). PostgreSQL (or in-memory fallback). |
| **`user-api`** | User profiles (display name, bio). MongoDB. Validates JWT with auth-api public key. |
| **`chat-api`** | RAG API: Weaviate retrieval, BM25 + Cohere rerank, OpenAI LLM, Redis semantic cache, Cassandra/in-memory chat memory. |
| **`frontend`** | Vite/React app; talks to the gateway at `/auth`, `/profiles`, `/chat`. |
| **`ingestion-worker`** | CLI: ingest PDFs into Weaviate, flush RAG semantic cache. No HTTP server. |
| **`libs/code-shared`** | Shared Python lib: `code_shared.llm` (base LLM + OpenAI), `code_shared.core` (exceptions only). Weaviate and Redis live in chat-api and ingestion-worker, not in the shared lib. |

Each app has its **own dependencies, Dockerfile, and CI workflow**. Auth-api and user-api (and optionally chat-api, ingestion-worker) install the shared lib before running tests.

- **Documentation**: [docs/](docs/) — [ADR](docs/adr/README.md), [API](docs/api/README.md), [DB](docs/db/README.md), [Services](docs/services/README.md).

## Prerequisites

- **Python 3.12**
- **Node.js 22** (frontend)
- **Docker + Docker Compose** (for full or light stack)
- **Git**

## Initial setup

```bash
git clone https://github.com/gitHuyNgo/production-ready-rag-us-law.git
cd production-ready-rag-us-law

python -m venv .venv
source .venv/bin/activate   # macOS / Linux
# .venv\Scripts\activate    # Windows
```

### Environment

- **Shared** (`app/.env`): Used by chat-api, user-api, api-gateway, frontend build. Copy from `app/.env.example` (if present) and set e.g. `OPENAI_API_KEY`, `COHERE_API_KEY`, `WEAVIATE_URL`, `REDIS_URL`, `AUTH_DB_URL`, gateway URLs.
- **Auth-api** (`app/auth-api/.env`): Optional; see `app/auth-api/.env.example`. For RS256 JWT, set `JWT_PRIVATE_KEY_PATH` and `JWT_PUBLIC_KEY_PATH` (e.g. to PEM files). In Docker, keys are often mounted under `/run/secrets/`.

## Install shared library

From the **repo root** (required for auth-api, user-api, chat-api, ingestion-worker):

```bash
pip install -e libs/code-shared
```

## Running services locally

### API Gateway

```bash
cd app/api-gateway
pip install -r requirements.txt   # if needed
make server   # uvicorn on port 8080
make test     # pytest
```

### Auth API

```bash
pip install -r app/auth-api/requirements.txt
cd app/auth-api
# Optional: generate test JWT keys in tests/fixtures/ (see .github/workflows/auth_api_ci.yaml)
make server   # port 8001
make test
```

### User API

```bash
pip install -r app/user-api/requirements.txt
cd app/user-api
# Optional: generate test JWT keys in tests/fixtures/ for profile tests
make server   # port 8002
make test
```

### Chat API

```bash
pip install -r app/chat-api/requirements.txt
cd app/chat-api
make server   # port 8000; needs WEAVIATE_URL, REDIS_URL, OPENAI_API_KEY
make test     # uses scripts/test.sh or pytest
```

### Ingestion worker

```bash
pip install -r app/ingestion-worker/requirements.txt
cd app/ingestion-worker
make test
make ingest ARGS="--data ./data --recreate"   # PDFs in ./data; --recreate resets Weaviate collection
```

### Frontend

```bash
cd app/frontend
npm install
npm run dev   # e.g. http://localhost:5173; proxy to gateway at 8080
```

## Docker Compose

From the **repo root**:

```bash
cp app/.env.example app/.env   # if needed; add secrets
# For auth-api: ensure app/auth-api/private.pem and public.pem exist (or mount elsewhere)
docker compose up -d
```

**Full stack** (`docker-compose.yml`): redis, weaviate, auth-db (Postgres), user-db (Mongo), cassandra, zookeeper, kafka, chat-api, frontend, auth-api, user-api, api-gateway.

| Service      | Host port |
|-------------|-----------|
| api-gateway | 8080      |
| auth-api    | 8001      |
| user-api    | 8002      |
| chat-api    | 8000      |
| frontend    | 3000      |
| Weaviate    | 8081      |
| Redis       | 6379      |

**Light stack** (no Cassandra/Kafka): `docker compose -f docker-compose.light.yml up -d`. Chat-api falls back to in-memory chat memory.

The **ingestion worker** is not run by Compose by default; run it as a one-off (e.g. `docker run` or CI job) to load PDFs and flush the semantic cache.

## CI/CD (GitHub Actions)

Workflows under `.github/workflows`:

| Workflow           | Tests / build |
|--------------------|----------------|
| `auth_api_ci.yaml` | Auth-api tests (shared lib + JWT keys generated in CI), build/push image |
| `user_api_ci.yaml` | User-api tests (shared lib + JWT keys in CI), build/push image |
| `api_gateway_ci.yaml` | Api-gateway tests, build/push image |
| `chat_api_ci.yaml` | Chat-api tests, build/push image |
| `ingestion_ci.yaml` | Ingestion-worker tests, build/push image |
| `frontend_ci.yaml` | Frontend build, build/push image |

Shared lib is installed in CI with `pip install -e libs/code-shared` where required. Auth-api and user-api workflows generate temporary RSA keys in `tests/fixtures/` so JWT-dependent tests pass.

Images are published to GHCR (`ghcr.io/<org>/<repo>/<service>:<tag>`) for use in Kubernetes, ECS, or other orchestrators.
