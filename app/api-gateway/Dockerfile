# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

COPY app/api-gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/api-gateway/src ./src

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 8080

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
