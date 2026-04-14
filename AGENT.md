# Nebiux ITC 2026 — Codex Instructions

Keep this repo aligned with the frozen V0.1 handoff docs.

- Start with [`docs/v0.1/README.md`](docs/v0.1/README.md) for final V0.1 status.
- Use [`docs/issue-18-setup-architecture.md`](docs/issue-18-setup-architecture.md) for the hosting and architecture decision record.
- Treat [`README.md`](README.md) as the top-level setup guide.
- Keep [`CLAUDE.md`](CLAUDE.md) in sync when repo guidance changes.

Repo shape:

- Web app, not Chrome extension.
- Frontend: React + Vite.
- Backend: FastAPI.
- Core work lives in preprocessing, retrieval artifacts, `/chat`, citations, and deployment docs.

Useful commands:

```bash
python scripts/check_corpus.py
python scripts/preprocess/run_pipeline.py
python scripts/build_index.py
uvicorn src.api.main:app --reload
cd frontend && npm run dev
pytest
```
