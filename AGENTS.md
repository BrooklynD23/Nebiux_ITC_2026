# Nebiux ITC 2026 — CPP Campus Knowledge Agent

## Project Overview

MISSA ITC 2026 competition entry — a **Campus Knowledge Agent** web application for Cal Poly Pomona.
Students ask natural-language questions about CPP and get grounded, cited answers from the official corpus.

## Current Phase

V0.1 — Sprint 0 contracts and parallel work setup.

## Architecture

Three-layer web app (NOT a Chrome extension):
1. **Frontend** — React chat UI with CPP branding
2. **Backend** — FastAPI + single LLM with one `search_corpus` tool (NOT council-of-agents)
3. **Retrieval** — Hybrid RAG: BM25 (Whoosh) + semantic (ChromaDB) with Reciprocal Rank Fusion

## Key Decisions

- Web app, NOT Chrome extension (competition requires "web application")
- Single LLM + one tool, NOT multi-agent (simplicity > complexity)
- Hybrid RAG (BM25 + semantic) for retrieval
- Corpus preprocessing (boilerplate stripping) is critical-path first task
- MVP: 7 items — preprocessor, search, LLM+tools, chat UI, citations, multi-turn, grounding

## File Locations

| Asset | Path |
|-------|------|
| Competition prompt | `competition-prompt/MISSA-ITC-AI-2026-Prompt.md` |
| Architecture guide | `cpp_hybrid_rag_uml_planning_guide.md` |
| Research report | `researchs/RAG-deep-research-report (1).md` |
| Feature inventory | `peer-review.md` |
| Adversarial review | `docs/adversarial-review-v0.1.md` |
| Implementation plan | `docs/implementation-plan-v0.1.md` |
| V0.1 source of truth | `docs/v0.1/README.md` |
| V0.1 sprint plan | `docs/v0.1/implementation-plan.md` |
| Corpus | `dataset/itc2026_ai_corpus/` (8,042 .md files + index.json) |

## Scoring (80pts total)

| Category | Points | Priority |
|----------|--------|----------|
| Features & Functionality | 30 | HIGHEST — core requirements must work |
| System Design | 20 | Architecture + corpus processing + tool calling |
| UI/UX | 20 | Clean chat interface, responsive, branded |
| Documentation & Presentation | 10 | README, architecture docs, live demo |

## Tech Stack

- **Backend**: Python, FastAPI, Uvicorn
- **LLM**: Google Gemini 2.5 Flash (default, free tier via Google AI Studio) or OpenAI gpt-4o-mini (fallback)
- **Embeddings**: sentence-transformers/all-MiniLM-L6-v2 (local)
- **Vector store**: ChromaDB
- **Lexical search**: Whoosh (BM25)
- **Frontend**: React + Vite (Streamlit fallback)
- **Analytics DB**: SQLite
- **Testing**: pytest

## Commands

```bash
# Verify corpus is installed (see dataset/README.md)
python scripts/check_corpus.py

# Preprocess corpus
python scripts/preprocess/run_pipeline.py

# Build search indexes
python scripts/build_index.py

# Run backend
uvicorn src.api.main:app --reload

# Run frontend
cd frontend && npm run dev

# Run tests
pytest

# Run eval harness
python scripts/eval/run_eval.py
```

## Implementation Sprints

1. **Sprint 0 — Contracts** — freeze preprocessing, API, citation, and eval interfaces
2. **Sprint 1 — Foundation** — preprocessing, backend skeleton, frontend on mocks
3. **Sprint 2 — Core E2E** — retrieval, tool loop, live chat integration
4. **Sprint 3 — Hardening & Showcase** — demo hardening and one optional showcase lane

Use `docs/v0.1/README.md` as the authoritative status board for contributors and agents.
