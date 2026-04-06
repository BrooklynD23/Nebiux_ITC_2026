#!/bin/sh
# Backend entrypoint — preprocesses corpus on first run, then starts the API.
set -e

CLEANED_DIR="data/cleaned"
INDEX_DIR="data/indexes"

# Run preprocessing only if cleaned output does not exist yet.
# Judges and new contributors get a working app after a single `docker compose up`.
if [ ! "$(ls -A $CLEANED_DIR 2>/dev/null)" ]; then
    echo "[entrypoint] Cleaned corpus not found — running preprocessing pipeline..."
    python scripts/preprocess/run_pipeline.py
    echo "[entrypoint] Preprocessing complete."
else
    echo "[entrypoint] Cleaned corpus found — skipping preprocessing."
fi

# Build search indexes if they don't exist yet.
if [ ! "$(ls -A $INDEX_DIR 2>/dev/null)" ]; then
    echo "[entrypoint] Indexes not found — building search indexes..."
    python scripts/build_index.py
    echo "[entrypoint] Indexes built."
else
    echo "[entrypoint] Indexes found — skipping index build."
fi

echo "[entrypoint] Starting API server..."
exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000
