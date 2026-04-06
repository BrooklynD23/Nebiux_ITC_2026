# V0.1 Source of Truth

Last updated: 2026-04-05

This folder is the canonical planning workspace for V0.1. If a top-level V0.1 document disagrees with anything in this folder, this folder wins.

## Current Status

- Current sprint: `Sprint 0 - Contracts and Parallel Work Setup`
- Project route: `Balanced core with one gated showcase lane`
- Team model: `3 contributors working in parallel after contracts freeze`
- Core demo target: local web app with chat, one search tool, grounded answers, citations, and multi-turn conversation

## Scope Guardrails

Keep:
- web app, not browser extension
- single LLM with one `search_corpus` tool
- preprocessing, retrieval, citations, refusal behavior, multi-turn chat
- one clean chat route

Defer unless Sprint 3 exit gate is already green:
- analytics dashboard
- extra routes beyond the core chat view
- reranker if hybrid retrieval already meets target
- more than one showcase feature

Cut for V0.1:
- council-of-agents
- persistent student profile
- voice and multilingual support
- mascot widget and extra surface area
- specialized tools beyond `search_corpus`

## Sprint Index

- [Implementation Plan](./implementation-plan.md)
- [Adversarial Review](./adversarial-review.md)
- [Sprint 0 - Contracts](./sprint-0-contracts.md)
- [Sprint 1 - Foundation](./sprint-1-foundation.md)
- [Sprint 2 - Core E2E](./sprint-2-core-e2e.md)
- [Sprint 3 - Hardening and Showcase](./sprint-3-hardening-showcase.md)

## Branch Naming Convention

Each contributor works on a branch prefixed with their lane letter:

| Contributor | Branch pattern | Example |
|---|---|---|
| A | `feat/a-<topic>` | `feat/a-preprocessing`, `feat/a-bm25-index` |
| B | `feat/b-<topic>` | `feat/b-api-skeleton`, `feat/b-tool-loop` |
| C | `feat/c-<topic>` | `feat/c-chat-ui`, `feat/c-eval-golden-set` |

Merge to `main` via pull request. Rebase before merging to keep history linear. Do not push directly to `main`.

## Ownership

### Contributor A
- Primary lane: corpus preprocessing and retrieval
- Likely paths: `dataset/`, `scripts/preprocess/`, `src/retrieval/`, `data/`

### Contributor B
- Primary lane: backend, tool loop, citations, conversation state
- Likely paths: `src/api/`, `src/agent/`, `src/config.py`, `.env.example`

### Contributor C
- Primary lane: frontend, thin eval set, planning status, demo-facing polish
- Likely paths: `frontend/`, `data/eval/`, `scripts/eval/`, `docs/v0.1/`

### Shared File Ownership

Files touched by multiple contributors have a single owner to prevent merge conflicts:

| File | Owner | Others may |
|---|---|---|
| `pyproject.toml` | B | Request changes via PR comment |
| `requirements.txt` | B | Request additions via PR comment |
| `src/config.py` | B | Import from it, never edit directly |
| `docs/v0.1/README.md` | C | Propose edits, C merges |
| `.gitignore` | B | Propose additions via PR comment |
| `CLAUDE.md` | C | Propose edits, C merges |

If you need a change in a file you don't own, add a comment on your PR tagging the owner. The owner makes the edit in their own branch or approves yours.

## Now

### Contributor A
- Freeze the preprocessing output contract:
  - `data/cleaned/` output conventions
  - `data/metadata.json` schema
  - `data/filter_report.json` schema
  - discard reasons and page-quality flags
- Confirm the boilerplate strategy is structure-based, not fixed-line-based.

### Contributor B
- Freeze the API and tool contract:
  - `POST /chat` request and response schema
  - `search_corpus(query, top_k)` contract
  - citation object shape
  - refusal and error status shape
- Lock the `conversation_id` behavior before frontend work starts.

### Contributor C
- Create mock chat fixtures that match the frozen response contract.
- Seed the first 12-15 golden cases across factual, follow-up, refusal, and adversarial categories.
- Keep this README current with sprint state, owners, blockers, and next work.

### Shared (all contributors)
- Agree on black/ruff/isort/pytest config (Contributor B commits `pyproject.toml`).
- Agree on eslint/prettier config (Contributor C commits frontend config).
- Confirm branch naming convention and shared file ownership rules above.
- Verify clean runs of `black --check .` and `ruff check .` before declaring Sprint 0 done.

## Next

After Sprint 0 exits:
- Contributor A moves to preprocessing implementation first, then BM25 retrieval.
- Contributor B builds the FastAPI skeleton against the frozen contract and retrieval stub.
- Contributor C builds the single-page React chat against mock responses first, then swaps to the live API in Sprint 2.

## Blockers

- No one should start irreversible implementation on `/chat`, citation rendering, or eval parsing until Sprint 0 contracts are frozen.
- No showcase feature starts until Sprint 2 exit criteria pass.

## Exit Gate for Current Sprint

Sprint 0 is complete only when:
- preprocessing outputs and discard taxonomy are documented
- `/chat`, `search_corpus`, citation, and error schemas are documented
- mock chat fixtures exist and match the schema
- the first 12-15 golden cases exist
- all three contributors agree that Sprint 1 work can proceed without schema churn

## Update Rules

- Any change to contracts, owners, or sprint order must update this file in the same change.
- Only one sprint can be marked active at a time.
- Each contributor should always have one `Now` item and one `Next` item listed here.
