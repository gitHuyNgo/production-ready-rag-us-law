# User-api Makefile – run from app/user-api/
SHELL := /bin/bash

APP_ENV_FILE ?= .env
export APP_ENV_FILE
export PYTHONPATH := $(shell pwd)

.PHONY: help test server serve

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "  test     Run pytest"
	@echo "  server   Start the API server with reload (dev)"
	@echo "  serve    Start the API server (e.g. Docker)"

test:
	pytest tests/ -v

server:
	uvicorn src.main:app --reload --host 127.0.0.1 --port 8002

serve:
	uvicorn src.main:app --host 0.0.0.0 --port 8002
