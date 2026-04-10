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

## Mascot & Media Assets

**Mascot**: Billy Bronco — Cal Poly Pomona's official mascot (anthropomorphic bronco)
**Style**: Modern flat vector 2D, friendly and approachable, CPP brand colors

### AI Generation Plans

| Asset Type | AI Tool | Plan Location | Purpose |
|------------|---------|---------------|---------|
| Static images & sprite sheets | Google Nano (Banana Pro) | `C:\Users\DangT\.windsurf\plans\nano-billy-bronco-prompt-f8da72.md` | Chat avatars, extension icons, animation frames |
| Landing page videos | Google Flow Lab | `C:\Users\DangT\.windsurf\plans\flowlab-video-prompts-f8da72.md` | Framer Motion integration, hero animations |
| Analytics dashboard | Google Stitch | `C:\Users\DangT\.windsurf\plans\stitch-ai-prompt-analytics-dashboard-f8da72.md` | Admin dashboard UI mockups |

### Character Design Specs
- **Body Structure**: **Quadruped horse stance** — stands on all four legs like a real horse (NOT bipedal/anthropomorphic)
- **Legs/Hooves**: Four gold hooves (#FFB81C) — two front legs can lift/gesture, two back legs support body
- **Proportions**: Natural horse body proportions — horizontal body, four-legged stance
- **Colors**: CPP Green `#00573D` (body), CPP Gold `#FFB81C` (mane/hooves), Cream `#FAF9F6` (muzzle)
- **Style**: Modern flat vector, clean 2px outlines, minimal shading, 2020s mascot aesthetic
- **Personality**: Helpful, intelligent, approachable, friendly horse character
- **Gestures**: Front hooves lift to wave, point, gesture — like a horse raising its front legs
- **Anatomy**: Natural quadruped horse (NOT bipedal anthropomorphic, NOT human-like proportions)

### Animation Frame Sets
1. **Idle/Breathing** — 8 frames for default chat presence
2. **Speaking/Talking** — 6 frames for response states
3. **Thinking/Processing** — 5 frames for search states
4. **Happy/Success** — 5 frames for positive feedback
5. **Apologetic/Refusal** — 5 frames for graceful "I don't know"
6. **Waving/Hello-Goodbye** — 6 frames for greeting/farewell

### Landing Page Videos (Flow Lab)
1. Hero Welcome Loop (10s)
2. Question-to-Answer Demo (8s)
3. Campus Topics Showcase (12s)
4. Multi-Turn Conversation (10s)
5. Source Attribution Trust Builder (8s)
6. Student Success Celebration (6s)
7. Mobile App Demo (8s)
8. Loading/Processing State (4s loop)
9. Graceful Error State (5s)
10. Call-to-Action Finale (6s)

### Asset Output Locations
```
assets/
  mascot/
    frames/          # Individual PNG frames from Nano
    icons/           # Extension icons, avatars
    sprites/         # CSS sprite sheets
    videos/          # Flow Lab MP4/WebM outputs
    source/          # Raw AI outputs
```

## Implementation Sprints

1. **Sprint 0 — Contracts** — freeze preprocessing, API, citation, and eval interfaces
2. **Sprint 1 — Foundation** — preprocessing, backend skeleton, frontend on mocks
3. **Sprint 2 — Core E2E** — retrieval, tool loop, live chat integration
4. **Sprint 3 — Hardening & Showcase** — demo hardening and one optional showcase lane

Use `docs/v0.1/README.md` as the authoritative status board for contributors and agents.
