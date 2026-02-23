#!/bin/bash
cd .. || exit 1
python -m src.ingestion.main "$@"