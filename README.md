# CPP Campus Knowledge Agent

Cal Poly Pomona campus assistant built for the MISSA ITC 2026 competition.

The repo is now standardized around a simple web-app architecture:

- `frontend/`: React + Vite chat UI
- `src/`: FastAPI backend
- `scripts/preprocess/`: offline corpus cleaning
- `scripts/build_index.py`: offline chunk manifest + BM25 index build
- `data/`: generated artifacts only

## Current Architecture

```
Browser (React + Vite)
        |
        v
FastAPI /chat API
        |
        v
Precomputed retrieval artifacts in data/
  - cleaned corpus
  - metadata.json
  - filter_report.json
  - chunks.jsonl
  - indexes/whoosh/
```

## Key Decisions

- **Frontend**: keep `React + Vite` for V0.1. Do not migrate to Next.js during the competition build unless the team later needs SSR or multi-route product pages.
- **Backend**: `Python 3.11 + FastAPI`.
- **Dev environment**: multi-container Docker Compose, not a single container. Python and Node have different toolchains and should stay isolated.
- **RAG storage**: no local relational DB is required for the MVP. Use file-based artifacts plus persisted index directories.
- **Runtime indexing**: preprocessing and index build are **offline / one-time startup** tasks, never per request.
- **Hosted deployment**: primary recommendation is a single VM deployment using `docker-compose.hosted.yml`; Vercel is acceptable only for a static frontend split, not for the full stack.

Detailed planning and rationale:

- [Issue #18 architecture plan](docs/issue-18-setup-architecture.md)
- [Judging and deployment guide](docs/judging-and-deployment.md)
- [V0.1 source of truth](docs/v0.1/README.md)

## Local Setup

### Prerequisites

- Docker Desktop for the containerized path
- Or Python 3.11+ and Node 20+ for the manual path
- The raw corpus under `dataset/itc2026_ai_corpus/`

See [dataset/README.md](dataset/README.md) for corpus setup.

### Option A: Docker Compose

This is the standard contributor setup.

```bash
git clone <repo-url>
cd Nebiux_ITC_2026

cp .env.example .env
docker compose up --build
```

What happens on first boot:

1. the backend verifies the raw corpus
2. the preprocessing pipeline writes `data/cleaned/`, `data/metadata.json`, `data/filter_report.json`, `data/freshness_manifest.json`, and `data/conflict_review.md`
3. the index build writes `data/chunks.jsonl` and `data/indexes/whoosh/`
4. the frontend starts on `http://localhost:5173`

Subsequent boots reuse the generated `data/` artifacts.

### Option B: Manual Local Run

```bash
git clone <repo-url>
cd Nebiux_ITC_2026

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]

cp .env.example .env
python scripts/check_corpus.py
python scripts/preprocess/run_pipeline.py
python scripts/build_index.py

uvicorn src.api.main:app --reload
```

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env.local
VITE_USE_MOCK=false npm run dev
```

Open `http://localhost:5173`.

## Environment Variables

### Backend

Use [`.env.example`](.env.example) as the source of truth.

- `LLM_PROVIDER=gemini|openai`
- `GEMINI_API_KEY=...`
- `OPENAI_API_KEY=...`
- `ADMIN_API_TOKEN=...` for privileged admin review endpoints and `/chat` debug mode
- `CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`
- `RAW_CORPUS_DIR=dataset/itc2026_ai_corpus`
- `DATA_DIR=data`
- `CONVERSATION_DB_PATH=data/conversations.db`
- `LOG_LEVEL=INFO|DEBUG|WARNING|ERROR|CRITICAL`
- `GROUNDING_MIN_TOP_SCORE=0.3`

### Frontend

Use [`frontend/.env.example`](frontend/.env.example).

- `VITE_USE_MOCK=false`
- `VITE_API_BASE_URL=` for hosted/static builds
- `VITE_DEV_PROXY_TARGET=http://127.0.0.1:8000` for local Vite proxying

## LLM Provider Note

The target provider for the competition build is **Gemini 2.5 Flash**, with **OpenAI gpt-4o-mini** as fallback. The repository does **not** include an API key, and judges are **not expected** to receive one from the team.

Current repo status matters here:

- the provider configuration contract exists in [src/config.py](src/config.py)
- the current `/chat` implementation uses provider tool calling, hybrid retrieval, conversation persistence, structured lifecycle logging, privileged debug mode, and a weak-retrieval refusal gate in [src/agent/tool_loop.py](src/agent/tool_loop.py)

## Admin Review Backend

The backend now supports a conversation-review path for the future admin dashboard without introducing student accounts:

- `conversation_id` remains the review key for all chat history and admin inspection
- `POST /chat` accepts `debug: true`, but only returns `debug_info` when the caller also presents `Authorization: Bearer <ADMIN_API_TOKEN>`
- `GET /admin/conversations` returns recent conversation summaries for dashboard list views
- `GET /admin/conversations/{conversation_id}` returns the persisted transcript plus turn-level review metadata
- structured JSON logs are emitted through the Python `logging` module for query lifecycle debugging in local dev

If you want live answers, set your own provider key in `.env`. For local UI-only work, the frontend can still run against mock mode.

## Hosted Deployment

Use the dedicated hosted compose file documented in [docs/judging-and-deployment.md](docs/judging-and-deployment.md):

```bash
cp .env.example .env
# Set CORS_ORIGINS and PUBLIC_API_BASE_URL for your server
docker compose -f docker-compose.hosted.yml up -d --build
```

Recommended hosting target: **Oracle Cloud single VM**.

Fallback: **AWS EC2** using the same compose file.

Not recommended as the primary host: **Vercel full-stack**, because the backend depends on persisted local artifacts and is not a good fit for serverless filesystem/runtime constraints.

## Storage Decision

No local relational DB is required for issue #18 or the MVP retrieval path.

Use the filesystem for the four different storage concerns:

1. **Source corpus**: `dataset/itc2026_ai_corpus/`
2. **Page and chunk metadata**: `data/metadata.json`, `data/chunks.jsonl`
3. **Persisted retrieval indexes**: `data/indexes/whoosh/` and reserved `data/indexes/chroma/`
4. **Runtime state**: SQLite-backed conversation persistence is enabled through `src/conversation/store.py` with default DB path `data/conversations.db` (configurable via `CONVERSATION_DB_PATH`)

## Repo Status

The repo now includes:

- offline preprocessing and index build
- Whoosh + Chroma retrieval artifacts
- provider-backed `search_corpus` tool calling
- SQLite-backed conversation persistence
- SQLite-backed admin review metadata keyed by `conversation_id`
- token-protected admin review endpoints
- structured JSON lifecycle logging and privileged chat debug responses
- retrieval normalization, ambiguity handling, and weak-retrieval refusal gating
