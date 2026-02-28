# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

COPY app/user-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/user-api/src ./src

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 8002

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8002"]

