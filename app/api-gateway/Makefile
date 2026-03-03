# API Gateway Makefile – run from app/api-gateway/
SHELL := /bin/bash
SCRIPTS := scripts

APP_ENV_FILE ?= .env
export APP_ENV_FILE
export PYTHONPATH := .

.PHONY: help server serve test

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "  server   Start the gateway with reload (dev)"
	@echo "  serve    Start the gateway (e.g. Docker)"
	@echo "  test     Run tests"

test:
	cd $(SCRIPTS) && bash test.sh

server:
	cd $(SCRIPTS) && bash server.sh

serve:
	uvicorn src.main:app --host 0.0.0.0 --port 8080
