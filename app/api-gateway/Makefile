# API Gateway Makefile – run from app/api-gateway/
SHELL := /bin/bash

APP_ENV_FILE ?= .env
export APP_ENV_FILE
export PYTHONPATH := .

.PHONY: help server serve

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "  server   Start the gateway with reload (dev)"
	@echo "  serve    Start the gateway (e.g. Docker)"

server:
	uvicorn src.main:app --reload --host 127.0.0.1 --port 8080

serve:
	uvicorn src.main:app --host 0.0.0.0 --port 8080
