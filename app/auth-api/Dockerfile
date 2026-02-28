# syntax=docker/dockerfile:1
# Build context must be repo root so libs/code-shared is available.
FROM python:3.12-slim

WORKDIR /app

COPY libs/code-shared /libs/code-shared
RUN pip install --no-cache-dir -e /libs/code-shared

COPY app/auth-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/auth-api/src ./src

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 8001

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]

