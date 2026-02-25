# Chat-api Makefile – run from app/chat-api/
SHELL := /bin/bash
SCRIPTS := scripts

# Shared env file (app/.env); override with make APP_ENV_FILE=/path/to/.env
APP_ENV_FILE ?= ../.env
export APP_ENV_FILE
export PYTHONPATH := .

.PHONY: help test server serve

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  test     Run pytest"
	@echo "  server   Start the API server with reload (dev)"
	@echo "  serve    Start the API server without reload (e.g. Docker)"

test:
	cd $(SCRIPTS) && bash test.sh

server:
	cd $(SCRIPTS) && bash server.sh

serve:
	uvicorn src.api.main:app --host 0.0.0.0 --port 8000
