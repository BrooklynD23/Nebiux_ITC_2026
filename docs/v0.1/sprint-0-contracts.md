# Sprint 0 - Contracts and Parallel Work Setup

Last updated: 2026-04-05

## Goal

Freeze the interfaces and handoff artifacts that allow three contributors to work in parallel without rework.

## Owners

- Contributor A: preprocessing outputs and corpus-quality taxonomy
- Contributor B: API, tool, citation, and conversation contracts
- Contributor C: mock fixtures, initial eval set, and source-of-truth status upkeep

## Work Items

### Contributor A
- Define `data/cleaned/` path and naming conventions.
- Define `data/metadata.json` schema.
- Define `data/filter_report.json` schema.
- Define discard reasons:
  - redirect
  - login-gated
  - too-short-after-cleaning
  - low-value-hub
  - boilerplate-only
- Define page-quality flags for downstream retrieval and citation work.

### Contributor B
- Define `POST /chat` request:
  - `conversation_id` optional
  - `message` required
- Define `POST /chat` response:
  - `conversation_id`
  - `status`
  - `answer_markdown`
  - `citations[]`
- Define `status` values:
  - `answered`
  - `not_found`
  - `error`
- Define `search_corpus(query, top_k)` output items:
  - `chunk_id`
  - `title`
  - `url`
  - `snippet`
  - `score`

### Contributor C
- Produce mock chat fixtures that match the frozen `POST /chat` response.
- Seed 12-15 golden cases:
  - factual
  - follow-up
  - out-of-scope
  - adversarial
- Update [README.md](./README.md) with sprint status and next tasks.

### LLM Provider Contract (Contributor B)
- Primary: Gemini 2.5 Flash via `google-genai` SDK (free tier via Google AI Studio)
- Fallback: OpenAI gpt-4o-mini via `openai` SDK
- Provider selected by: `LLM_PROVIDER` env var ("gemini" | "openai"), default "gemini"
- API key env vars:
  - `GEMINI_API_KEY` — required when `LLM_PROVIDER=gemini`
  - `OPENAI_API_KEY` — required when `LLM_PROVIDER=openai`
- `src/config.py` must expose a single `get_llm_client()` function that returns the correct client based on `LLM_PROVIDER`
- Callers never import provider SDKs directly; all LLM calls go through the abstraction

### Shared — CI and Tooling Agreement

All three contributors agree on the following before Sprint 1:
- Python formatter: `black` (config in `pyproject.toml`)
- Python linter: `ruff` (config in `pyproject.toml`)
- Import sorter: `isort` (profile = black, config in `pyproject.toml`)
- Test runner: `pytest` (config in `pyproject.toml`)
- Frontend linter: `eslint` + `prettier` (config in `frontend/`)
- Minimum test coverage target: 80%
- PR merge rule: at least one approval from a non-author contributor

Contributor B owns `pyproject.toml` and commits the agreed config. Contributor C owns frontend tooling config.

## Artifacts to Freeze

- preprocessing contract
- API contract
- citation contract
- mock response fixtures
- initial eval case format
- LLM provider contract (env vars, SDK choice, abstraction interface)
- `pyproject.toml` with black, ruff, isort, and pytest configuration
- `frontend/` with eslint and prettier configuration
- `.env.example` documenting all required environment variables

## Exit Criteria

- all contracts are documented in this folder
- frontend can build against mocks without guessing fields
- backend can build against retrieval stubs without changing the API shape later
- eval cases can parse the response shape without special-case logic
- LLM provider contract (env vars, SDK choice, `get_llm_client()` interface) is documented
- `.env.example` documents `LLM_PROVIDER`, `GEMINI_API_KEY`, and `OPENAI_API_KEY`
- `pyproject.toml` has black, ruff, isort, and pytest config committed
- frontend eslint and prettier config is committed
- branch naming convention and shared file ownership are documented in the README
- all three contributors confirm they can run `black --check .` and `ruff check .` cleanly
- all three contributors confirm they have tested env var reading with `.env.example`
