# Nebiux ITC 2026 — Claude Instructions

## Current State

- V0.1 is still in Sprint 0 contracts and parallel work setup.
- [`docs/v0.1/README.md`](docs/v0.1/README.md) is the canonical status board.
- [`README.md`](README.md) is the top-level setup guide.
- [`AGENT.md`](AGENT.md) mirrors these repo instructions for Codex.
- [`AGENTS.md`](AGENTS.md) is kept only as a compatibility shim.

## Architecture

- Web app, not Chrome extension.
- Frontend: React + Vite chat UI.
- Backend: FastAPI with one `search_corpus` tool.
- Retrieval: hybrid BM25 + semantic RAG.
- Preprocessing pipeline writes `data/cleaned/`, `data/metadata.json`, `data/filter_report.json`, `data/freshness_manifest.json`, and `data/conflict_review.md`.
- [`scripts/preprocess/freshness.py`](scripts/preprocess/freshness.py) and [`scripts/preprocess/conflicts.py`](scripts/preprocess/conflicts.py) are present and tested.

## Important Paths

| Asset | Path |
|---|---|
| Status board | [`docs/v0.1/README.md`](docs/v0.1/README.md) |
| Setup guide | [`README.md`](README.md) |
| Preprocess pipeline | [`scripts/preprocess/run_pipeline.py`](scripts/preprocess/run_pipeline.py) |
| Freshness helpers | [`scripts/preprocess/freshness.py`](scripts/preprocess/freshness.py) |
| Conflict helpers | [`scripts/preprocess/conflicts.py`](scripts/preprocess/conflicts.py) |
| Index build | [`scripts/build_index.py`](scripts/build_index.py) |
| App settings | [`src/settings.py`](src/settings.py) |
| LLM config | [`src/config.py`](src/config.py) |
| Backend entrypoint | [`src/api/main.py`](src/api/main.py) |
| Frontend | [`frontend/`](frontend/) |

## Commands

```bash
python scripts/check_corpus.py
python scripts/preprocess/run_pipeline.py
python scripts/build_index.py
uvicorn src.api.main:app --reload
cd frontend && npm run dev
pytest
python scripts/eval/run_eval.py
```

## Update Rules

- Update [`docs/v0.1/README.md`](docs/v0.1/README.md) in the same change whenever contracts, owners, or sprint order change.
- Keep this file aligned with [`AGENT.md`](AGENT.md) when repo guidance changes.
