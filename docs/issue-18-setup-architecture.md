# Setup Architecture #18

GitHub issue: [#18](https://github.com/BrooklynD23/Nebiux_ITC_2026/issues/18)

## Scope

This document captures the architecture decision, repo audit, implementation plan, and acceptance criteria for issue `Setup architecture`.

The issue body is empty, so the planning baseline for this document comes from:

- [competition-prompt/MISSA-ITC-AI-2026-Prompt.md](../competition-prompt/MISSA-ITC-AI-2026-Prompt.md)
- [docs/v0.1/README.md](./v0.1/README.md)
- [docs/v0.1/implementation-plan.md](./v0.1/implementation-plan.md)
- [docs/v0.1/sprint-0-contracts.md](./v0.1/sprint-0-contracts.md)
- [scripts/preprocess/freshness.py](../scripts/preprocess/freshness.py)
- [scripts/preprocess/conflicts.py](../scripts/preprocess/conflicts.py)
- [tests/test_freshness.py](../tests/test_freshness.py)
- [tests/test_conflicts.py](../tests/test_conflicts.py)

## 1. Repo Audit

### Current frontend / backend / infra state

- Frontend already exists as `React + Vite`, not Next.js:
  - [frontend/package.json](../frontend/package.json)
  - [frontend/src/App.tsx](../frontend/src/App.tsx)
  - [frontend/src/hooks/useChat.ts](../frontend/src/hooks/useChat.ts)
- Backend already exists as FastAPI with a stub `/chat` route:
  - [src/api/main.py](../src/api/main.py)
  - [src/api/routes.py](../src/api/routes.py)
  - [src/agent/tool_loop.py](../src/agent/tool_loop.py)
- Retrieval was contract-only before this issue:
  - [src/retrieval/interface.py](../src/retrieval/interface.py)
  - [src/retrieval/stub.py](../src/retrieval/stub.py)
- Preprocessing exists and is test-backed:
  - [scripts/preprocess/run_pipeline.py](../scripts/preprocess/run_pipeline.py)
  - [tests/test_pipeline.py](../tests/test_pipeline.py)

### Relevant files reviewed

- Competition requirements:
  - [competition-prompt/MISSA-ITC-AI-2026-Prompt.md](../competition-prompt/MISSA-ITC-AI-2026-Prompt.md)
- Current architecture and sprint docs:
  - [docs/v0.1/README.md](./v0.1/README.md)
  - [docs/v0.1/implementation-plan.md](./v0.1/implementation-plan.md)
  - [docs/v0.1/sprint-0-contracts.md](./v0.1/sprint-0-contracts.md)
- Dataset and preprocessing:
  - [dataset/README.md](../dataset/README.md)
  - [scripts/preprocess/strip_boilerplate.py](../scripts/preprocess/strip_boilerplate.py)
  - [scripts/preprocess/filter_corpus.py](../scripts/preprocess/filter_corpus.py)
  - [scripts/preprocess/extract_metadata.py](../scripts/preprocess/extract_metadata.py)
  - [scripts/preprocess/freshness.py](../scripts/preprocess/freshness.py)
  - [scripts/preprocess/conflicts.py](../scripts/preprocess/conflicts.py)
  - [tests/test_freshness.py](../tests/test_freshness.py)
  - [tests/test_conflicts.py](../tests/test_conflicts.py)
- Infra and env handling:
  - [Dockerfile](../Dockerfile)
  - [docker-compose.yml](../docker-compose.yml)
  - [docker/entrypoint.sh](../docker/entrypoint.sh)
  - [.env.example](../.env.example)
  - [frontend/.env.example](../frontend/.env.example)

### Gaps, risks, ambiguities found

- The repo described a runnable Docker path, but the old backend image depended on a missing `requirements.txt` and a missing `scripts/build_index.py`.
- The frontend env contract was inconsistent between compose and runtime code.
- The frontend defaulted to mock mode, which hid backend integration by default.
- The preprocessing helpers are now in the production tree, and the main pipeline writes `data/cleaned/`, `data/metadata.json`, `data/filter_report.json`, `data/freshness_manifest.json`, and `data/conflict_review.md`.
- The old notebook/output paths have been deleted, so any reference to `preprocessing_pipeline_test/` is historical only.
- The repo had no explicit judge/deployment guide and no hosted deployment compose file.
- The current backend still uses a scaffold tool loop, so issue #18 should standardize architecture without pretending that the full hybrid retriever is already complete.

## 2. Architecture Recommendation

### Recommended local development architecture

Use **Docker Compose with two containers**:

1. `backend` for Python/FastAPI
2. `frontend` for React/Vite

Why:

- separate Python and Node toolchains cleanly
- hot-reload remains simple
- contributors avoid local dependency drift
- no extra DB container is needed for the MVP

Do **not** use a single all-in-one container. The only advantage would be one process boundary, and that does not outweigh the worse contributor experience.

### Recommended application architecture

- Keep the current **FastAPI backend**.
- Keep the current **React + Vite frontend** for V0.1.
- Do **not** migrate to Next.js in this issue.

Rationale:

- the app is a single chat route, so SSR gives little value
- Vite is already implemented
- the competition values working features and documentation more than framework novelty
- a Next.js migration would create churn without improving retrieval quality

### Ingestion vs runtime query workflow

- **Offline / one-time startup**:
  - raw corpus validation
  - boilerplate stripping
  - filtering
  - metadata extraction
  - freshness scoring
  - conflict review generation
  - chunk manifest build
  - BM25 index build
- **Runtime request path**:
  - `/chat`
  - retrieval against precomputed artifacts
  - tool loop / answer composition

Do **not** build indexes on every startup and never during a user request.

### RAG storage decision

#### Explicit answer

**No local relational DB is needed for the MVP.**

#### Split by storage concern

1. Source corpus files
   - keep in `dataset/itc2026_ai_corpus/`
   - untracked, read-only input
2. Chunk metadata
   - store in `data/metadata.json`, `data/freshness_manifest.json`, and `data/chunks.jsonl`
3. Preprocessing review artifacts
   - store the human-readable conflict review in `data/conflict_review.md`
4. Embedding / vector index
   - reserve `data/indexes/chroma/`
5. Runtime query state / logs
   - in-memory conversation state for now
   - optional SQLite later if analytics or persisted conversations become necessary

#### Why not Postgres or SQLite now

- only ~8k source pages
- the core retrieval workload is read-heavy and artifact-based
- the team is time-constrained
- judges need a reliable local run path more than a fully normalized data model
- adding a DB service would increase ops work without solving the main competition risks

### Hosting architecture comparison

| Option | Decision | Why |
|---|---|---|
| Vercel | Reject as primary backend host | serverless filesystem/runtime model is a poor fit for persisted local retrieval artifacts |
| AWS free tier | Accept as fallback | familiar and workable, but micro-tier memory is tighter for Python + local indexes |
| Google Cloud VM | Recommend as primary | enough headroom for a single VM running Docker Compose with persisted local artifacts |

### Final deployment recommendation

Primary:

- **single Google Cloud VM deployment**
- backend + static frontend on the same host
- use [docker-compose.hosted.yml](../docker-compose.hosted.yml)

Optional split:

- Vercel static frontend
- Google Cloud VM or AWS backend

Only use the split if the team specifically wants Vercel for the frontend URL. It adds CORS and deployment coordination that the team can avoid with a single VM.

## 3. Plan for Issue #18

### Phased task list

1. Normalize env and runtime contracts
2. Fix Docker and startup bootstrap
3. Add the missing retrieval artifact build step
4. Document local + hosted deployment paths
5. Re-run repo review and validation

### Files to create or update

- Infra / env:
  - [Dockerfile](../Dockerfile)
  - [docker-compose.yml](../docker-compose.yml)
  - [docker-compose.hosted.yml](../docker-compose.hosted.yml)
  - [docker/entrypoint.sh](../docker/entrypoint.sh)
  - [.env.example](../.env.example)
  - [frontend/.env.example](../frontend/.env.example)
- Runtime config:
  - [src/settings.py](../src/settings.py)
  - [src/config.py](../src/config.py)
  - [src/api/main.py](../src/api/main.py)
- Retrieval artifact build:
  - [scripts/build_index.py](../scripts/build_index.py)
  - [scripts/check_corpus.py](../scripts/check_corpus.py)
- Frontend runtime:
  - [frontend/Dockerfile](../frontend/Dockerfile)
  - [frontend/package.json](../frontend/package.json)
  - [frontend/vite.config.ts](../frontend/vite.config.ts)
  - [frontend/src/api/client.ts](../frontend/src/api/client.ts)
- Docs:
  - [README.md](../README.md)
  - [docs/judging-and-deployment.md](./judging-and-deployment.md)
  - [docs/v0.1/README.md](./v0.1/README.md)

### Acceptance criteria

- `docker compose up --build` is internally consistent
- local contributor setup is documented with one standard path
- hosted Google Cloud VM deployment path is documented and containerized
- backend CORS origins are env-driven
- frontend mock/live behavior is explicit
- retrieval artifacts have a concrete on-disk contract
- the repo explicitly documents that a full DB is not required for the MVP

### Rollback / simplification path

If the retrieval artifact work grows too heavy during Sprint 1:

- keep `scripts/build_index.py` as chunk-manifest-only
- defer Chroma/vector build
- keep runtime on stub retrieval until Sprint 2

What should **not** be rolled back:

- env contract cleanup
- Docker/bootstrap fixes
- judge/deployment docs
- the decision to avoid a DB service for MVP architecture
