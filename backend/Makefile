# Backend Makefile – run from backend/
SHELL := /bin/bash
SCRIPTS := scripts

.PHONY: help test ingest server

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  test     Run pytest"
	@echo "  ingest   Run ingestion (optional: make ingest ARGS='path/to/docs')"
	@echo "  server   Start the API server (uvicorn)"

test:
	cd $(SCRIPTS) && bash test.sh

ingest:
	cd $(SCRIPTS) && bash ingestion.sh $(ARGS)

server:
	cd $(SCRIPTS) && bash server.sh
