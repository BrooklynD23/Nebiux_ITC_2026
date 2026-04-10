# Nebiux ITC 2026 — Codex Instructions

## Current State

- V0.1 is still in Sprint 0 contracts and parallel work setup.
- [`docs/v0.1/README.md`](docs/v0.1/README.md) is the canonical status board.
- [`README.md`](README.md) is the top-level setup guide.
- [`CLAUDE.md`](CLAUDE.md) mirrors these repo instructions for Claude.
- [`AGENTS.md`](AGENTS.md) is kept only as a compatibility shim.

## Repo Shape

- Web app, not Chrome extension.
- Frontend: React + Vite chat UI.
- Backend: FastAPI with one `search_corpus` tool.
- Retrieval: hybrid BM25 + semantic RAG.
- Current preprocessing outputs are `data/cleaned/`, `data/metadata.json`, and `data/filter_report.json`.
- [`scripts/preprocess/freshness.py`](scripts/preprocess/freshness.py) and [`scripts/preprocess/conflicts.py`](scripts/preprocess/conflicts.py) exist with tests, but the main pipeline still does not emit `data/freshness_manifest.json` or `data/conflict_review.md`.

## What To Touch

| Area | Path |
|---|---|
| Status board | [`docs/v0.1/README.md`](docs/v0.1/README.md) |
| Setup guide | [`README.md`](README.md) |
| Preprocess pipeline | [`scripts/preprocess/run_pipeline.py`](scripts/preprocess/run_pipeline.py) |
| Freshness helpers | [`scripts/preprocess/freshness.py`](scripts/preprocess/freshness.py) |
| Conflict helpers | [`scripts/preprocess/conflicts.py`](scripts/preprocess/conflicts.py) |
| Index build | [`scripts/build_index.py`](scripts/build_index.py) |
| Settings | [`src/settings.py`](src/settings.py) |
| Config | [`src/config.py`](src/config.py) |
| Backend API | [`src/api/main.py`](src/api/main.py) |
| Frontend | [`frontend/`](frontend/) |

## Common Commands

```bash
python scripts/check_corpus.py
python scripts/preprocess/run_pipeline.py
python scripts/build_index.py
uvicorn src.api.main:app --reload
cd frontend && npm run dev
pytest
python scripts/eval/run_eval.py
```

## Working Rules

- Keep [`CLAUDE.md`](CLAUDE.md) and [`AGENT.md`](AGENT.md) in sync when repo guidance changes.
- Update [`docs/v0.1/README.md`](docs/v0.1/README.md) whenever the sprint board, owners, or contracts change.
- Treat freshness/conflict artifact generation as pending until `run_pipeline.py` is updated.
