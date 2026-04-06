FROM python:3.11-slim

WORKDIR /app

# System deps needed by sentence-transformers and Whoosh
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer caches unless requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY src/ ./src/
COPY scripts/ ./scripts/

# Data directories are mounted at runtime — create empty placeholders so
# the container starts without errors if volumes haven't been populated yet.
RUN mkdir -p data/cleaned data/indexes dataset/itc2026_ai_corpus

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
