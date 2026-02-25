End-to-end deployment of a scalable RAG pipeline for U.S. legal QA, featuring microservices, vector-based retrieval, CI/CD automation, and high-performance LLM serving.

## Overview

This repo is organized as a small **microservice** system:

- **`libs/code-shared`**: Shared Python library with:
  - `code_shared.llm` – base LLM interfaces and OpenAI client.
  - `code_shared.core` – config, vector store (Weaviate), and semantic cache (Redis).
- **`app/chat-api`**: FastAPI backend that exposes the RAG API.
- **`app/ingestion-worker`**: Batch worker that ingests PDFs into Weaviate and flushes the semantic cache.
- **`app/frontend`**: Vite/React frontend that talks to `chat-api`.

Each service has its **own dependencies, Dockerfile, and CI workflow**, but they share the same environment config (`app/.env`) and the `code-shared` library.

## Prerequisites

- Python **3.12**
- Node.js **22** (for the frontend)
- Docker + Docker Compose (for containerized runs)
- Git

## Initial setup

```bash
git clone https://github.com/gitHuyNgo/production-ready-rag-us-law.git
cd production-ready-rag-us-law

python -m venv .venv        # or python3 -m venv .venv
source .venv/bin/activate   # macOS / Linux
# .venv\Scripts\activate    # Windows (PowerShell / cmd)
```

### Configure env (shared for all services)

```bash
cd app
cp .env.example .env
# Edit app/.env and fill in:
# - OPENAI_API_KEY
# - COHERE_API_KEY
# - WEAVIATE_URL (default points at docker-compose service)
# - REDIS_URL (default points at docker-compose service)
```

> `app/.env` is the **single source of truth** for environment variables used by `chat-api` and `ingestion-worker`.

## Install shared library

From the **repo root**:

```bash
cd production-ready-rag-us-law
pip install -e libs/code-shared
```

This installs the `code_shared` package (LLM + core vector-store/cache code) that both backend services use.

## Chat API (backend service)

### Install dependencies

From the repo root:

```bash
pip install -r app/chat-api/requirements.txt
```

### Run tests

```bash
cd app/chat-api
make test
```

### Run the API locally (without Docker)

```bash
cd app/chat-api
make server   # dev with reload

# or, directly:
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.  
Swagger UI: `http://localhost:8000/docs`

## Ingestion worker

The ingestion worker reads PDFs and loads chunks into Weaviate using the same `code_shared.core` stack, then flushes the semantic cache.

### Install dependencies

From the repo root:

```bash
pip install -r app/ingestion-worker/requirements.txt
```

### Run tests

```bash
cd app/ingestion-worker
make test
```

### Run ingestion locally

```bash
cd app/ingestion-worker
make ingest ARGS="--data ./data --recreate"
```

- **`--data`**: directory containing PDFs (default `./data`).
- **`--recreate`**: drop and recreate the Weaviate collection (useful when changing embedding dimensions).

## Frontend

From the repo root:

```bash
cd app/frontend
npm install
npm run dev       # local dev server
```

The dev server URL is whatever Vite prints (typically `http://localhost:5173`).

## Running everything with Docker Compose

From the **repo root**:

```bash
cd production-ready-rag-us-law
cp app/.env.example app/.env   # if you haven't already
# Fill in secrets in app/.env

docker compose up -d
```

Services:

- **`redis`** – Redis Stack (semantic cache).
- **`weaviate`** – Weaviate vector DB.
- **`chat-api`** – FastAPI backend (exposed on `http://localhost:8000`).
- **`frontend`** – React app served via Nginx (exposed on `http://localhost:3000`).

Compose uses:

- `app/chat-api/Dockerfile` for the API image.
- `app/frontend/Dockerfile` for the frontend image.

> The ingestion worker also has a Dockerfile (`app/ingestion-worker/Dockerfile`) and its own CI workflow. You can run it as a one-off job container when needed (e.g. in Kubernetes or via `docker run`).

## CI/CD (GitHub Actions)

Workflows under `.github/workflows`:

- **`chat_api_ci.yaml`** – runs chat-api tests and builds/pushes `chat-api` image.
- **`ingestion_ci.yaml`** – runs ingestion-worker tests and builds/pushes `ingestion-worker` image.
- **`frontend_ci.yaml`** – builds the frontend and builds/pushes `frontend` image.

All backend services depend on the shared `code-shared` library, which is installed in CI with:

```bash
pip install -e libs/code-shared
```

You can use the published images from GHCR (under `ghcr.io/<your-org>/<your-repo>/...`) in your own deployment manifests (Kubernetes, ECS, etc.).
