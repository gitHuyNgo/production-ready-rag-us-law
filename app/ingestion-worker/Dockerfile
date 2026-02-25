# syntax=docker/dockerfile:1
# Build context must be repo root so libs/code-shared is available.
FROM python:3.12-slim

WORKDIR /app

# Install shared lib first
COPY libs/code-shared /libs/code-shared
RUN pip install --no-cache-dir -e /libs/code-shared

# Ingestion-worker dependencies and app
COPY app/ingestion-worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ingestion-worker/src ./src
COPY app/ingestion-worker/Makefile .
COPY app/ingestion-worker/ingestion.sh .

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Default: run ingestion (override with args, e.g. --data /data --recreate)
ENTRYPOINT ["python", "-m", "src.main"]
CMD ["--data", "/data"]
