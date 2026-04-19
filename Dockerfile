FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

ARG INSTALL_SEMANTIC=true

WORKDIR /app

# System deps needed by sentence-transformers and Whoosh
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer caches unless project metadata changes)
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --upgrade pip && \
    if [ "$INSTALL_SEMANTIC" = "true" ]; then \
        pip install ".[semantic]"; \
    else \
        pip install "."; \
    fi

COPY scripts/ ./scripts/

# Data directories are mounted at runtime — create empty placeholders so
# the container starts without errors if volumes haven't been populated yet.
RUN mkdir -p data/cleaned data/indexes dataset/itc2026_ai_corpus

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
