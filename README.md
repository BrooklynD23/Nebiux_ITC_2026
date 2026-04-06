# CPP Campus Knowledge Agent

A web-based Campus Knowledge Agent for Cal Poly Pomona — built for the MISSA ITC 2026 competition.

Ask natural-language questions about CPP admissions, academics, campus services, financial aid, and student life. Get accurate, grounded answers with source citations from official CPP web content.

## Architecture

```
Frontend (React)  →  Backend (FastAPI + LLM)  →  Retrieval (Hybrid RAG)
     Chat UI            Tool Calling              BM25 + Semantic Search
     Citations          Grounding                 8,042 CPP pages
```

## Quick Start

### Option A — Docker (recommended, works on Windows / macOS / Linux)

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) and an OpenAI API key.

```bash
# 1. Clone the repo
git clone <repo-url>
cd Nebiux_ITC_2026

# 2. Drop the corpus into place (see dataset/README.md for the download link)
#    Expected: dataset/itc2026_ai_corpus/ with 8,000+ .md files

# 3. Set your API key
cp .env.example .env
#    Edit .env and set OPENAI_API_KEY=sk-...

# 4. Build and start everything
docker compose up --build
```

Open http://localhost:5173. The backend preprocesses the corpus automatically on first launch (takes ~2–5 minutes). Subsequent starts are instant.

---

### Option B — Manual setup (WSL2 / macOS / Linux)

**Prerequisites:** Python 3.11+, Node.js 18+, OpenAI API key.

```bash
# Clone and enter project
git clone <repo-url>
cd Nebiux_ITC_2026

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..

# Set your LLM API key (Gemini is free — get one at https://aistudio.google.com)
cp .env.example .env
# Edit .env: paste your GEMINI_API_KEY (or switch to openai and add OPENAI_API_KEY)

# Verify corpus is installed (see dataset/README.md)
python scripts/check_corpus.py

# Preprocess corpus and build indexes
python scripts/preprocess/run_pipeline.py
python scripts/build_index.py

# Start backend
uvicorn src.api.main:app --reload &

# Start frontend
cd frontend && npm run dev
```

Open http://localhost:5173 and start asking questions.

## Features

- **Conversational Chat** — natural-language Q&A about Cal Poly Pomona
- **Grounded Responses** — answers come only from official CPP content, never hallucinated
- **Source Citations** — every answer links to the original CPP web page
- **Multi-turn Conversation** — follow-up questions maintain context
- **Tool Calling** — LLM uses function calling to search the corpus
- **Hybrid Search** — combines keyword (BM25) and semantic search for best results

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI + Uvicorn |
| LLM | Google Gemini 2.5 Flash (configurable) |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 |
| Vector Store | ChromaDB |
| Lexical Search | Whoosh (BM25) |
| Frontend | React + Vite |
| Testing | pytest |

## Project Structure

```
Nebiux_ITC_2026/
├── src/                    # Backend source code
│   ├── api/                # FastAPI endpoints
│   ├── agent/              # LLM integration, tools, citations
│   └── retrieval/          # Search pipeline (BM25, embeddings, hybrid)
├── frontend/               # React chat UI
├── scripts/                # Preprocessing, indexing, evaluation
│   ├── preprocess/         # Corpus cleaning pipeline
│   ├── eval/               # Evaluation harness
│   └── build_index.py      # Index builder
├── dataset/                # CPP corpus (8,042 markdown pages)
├── data/                   # Processed outputs (cleaned corpus, indexes)
├── tests/                  # Test suite
├── docs/                   # Documentation
└── competition-prompt/     # Official competition brief
```

## Team

Nebiux — Cal Poly Pomona

## Status

V0.1 — Implementation in progress.
