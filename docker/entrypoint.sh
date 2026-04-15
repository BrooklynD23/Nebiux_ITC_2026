#!/bin/sh
# Backend entrypoint — builds artifacts if needed, then starts the API.
set -eu

RAW_CORPUS_DIR="${RAW_CORPUS_DIR:-dataset/itc2026_ai_corpus}"
DATA_DIR="${DATA_DIR:-data}"
CLEANED_DIR="${DATA_DIR}/cleaned"
INDEX_DIR="${DATA_DIR}/indexes"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

mkdir -p "$CLEANED_DIR" "$INDEX_DIR"

if [ "${AUTO_BUILD_ARTIFACTS:-true}" = "true" ]; then
    echo "[entrypoint] Verifying corpus at ${RAW_CORPUS_DIR}..."
    python scripts/check_corpus.py --corpus-dir "$RAW_CORPUS_DIR"

    if [ ! "$(ls -A "$CLEANED_DIR" 2>/dev/null)" ]; then
        echo "[entrypoint] Cleaned corpus not found — running preprocessing pipeline..."
        python scripts/preprocess/run_pipeline.py \
            --corpus-dir "$RAW_CORPUS_DIR" \
            --output-dir "$DATA_DIR"
        echo "[entrypoint] Preprocessing complete."
    else
        echo "[entrypoint] Cleaned corpus found — skipping preprocessing."
    fi

    if [ ! -f "${DATA_DIR}/chunks.jsonl" ] || [ ! "$(ls -A "${INDEX_DIR}/whoosh" 2>/dev/null)" ] || ! INDEX_DIR="$INDEX_DIR" python -c "import os, sys; from pathlib import Path; from src.retrieval.chroma_index import chroma_collection_exists; sys.exit(0 if chroma_collection_exists(Path(os.environ['INDEX_DIR']) / 'chroma') else 1)"; then
        echo "[entrypoint] Search artifacts not found — building chunk manifest and BM25 index..."
        python scripts/build_index.py \
            --cleaned-dir "$CLEANED_DIR" \
            --metadata-path "${DATA_DIR}/metadata.json" \
            --output-dir "$DATA_DIR"
        echo "[entrypoint] Search artifacts built."
    else
        echo "[entrypoint] Search artifacts found — skipping rebuild."
    fi
else
    echo "[entrypoint] AUTO_BUILD_ARTIFACTS=false — skipping preprocessing and index build."
fi

echo "[entrypoint] Starting API server on ${HOST}:${PORT}..."
if [ "${UVICORN_RELOAD:-false}" = "true" ]; then
    exec uvicorn src.api.main:app --host "$HOST" --port "$PORT" --reload
fi

exec uvicorn src.api.main:app --host "$HOST" --port "$PORT"
