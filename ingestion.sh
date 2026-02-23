#!/bin/bash
cd backend || exit 1
python -m src.ingestion.main "$@"