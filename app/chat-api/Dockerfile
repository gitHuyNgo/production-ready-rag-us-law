# syntax=docker/dockerfile:1
# Build context must be repo root so libs/code-shared is available.
FROM python:3.12-slim

WORKDIR /app

# Install make for Makefile targets
RUN apt-get update && apt-get install -y --no-install-recommends make \
    && rm -rf /var/lib/apt/lists/*

# Install shared lib first (must be built from repo root: docker build -f app/chat-api/Dockerfile .)
COPY libs/code-shared /libs/code-shared
RUN pip install --no-cache-dir -e /libs/code-shared

# Chat-api dependencies and app
COPY app/chat-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/chat-api/src ./src
COPY app/chat-api/Makefile ./

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["make", "serve"]
