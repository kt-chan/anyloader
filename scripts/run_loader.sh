#!/bin/bash

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Starting anyLoader ingestion..."
cd "$PROJECT_ROOT"

# Load environment variables if .env exists
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Ensure Python 3 is used
python3 src/loader/ingest.py

echo "Ingestion process completed."
