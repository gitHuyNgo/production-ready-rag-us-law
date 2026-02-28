SHELL := /bin/bash

# Local .env in this service dir; override with make APP_ENV_FILE=/path/to/.env
APP_ENV_FILE ?= .env
export APP_ENV_FILE
export PYTHONPATH := .:../../libs/code-shared/src

.PHONY: help ingest test

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  ingest   Run the ingestion pipeline (optional: make ingest ARGS='--data ./data --recreate')"
	@echo "  test     Run pytest"

ingest:
	bash ingestion.sh $(ARGS)

test:
	PYTHONPATH=. pytest tests/ -v

