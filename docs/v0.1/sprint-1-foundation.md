# Sprint 1 - Foundation

Last updated: 2026-04-05

## Goal

Create three parallel work lanes that build real foundations without waiting on end-to-end integration.

## Contributor A - Corpus and Retrieval Foundation

Primary outputs:
- structure-based boilerplate stripping
- redirect and login-gate filtering
- cleaned markdown artifacts
- metadata manifest
- filter report

Acceptance criteria:
- cleaned files preserve headings and tables
- duplicate nav and social blocks are removed
- excluded files include explicit discard reasons

Likely paths:
- `scripts/preprocess/`
- `data/`
- `tests/test_strip_boilerplate.py`
- `tests/test_filter_corpus.py`

## Contributor B - Backend Foundation

Primary outputs:
- FastAPI skeleton
- `GET /health`
- stubbed `POST /chat`
- citation normalization helpers for `index.json`
- retrieval interface stub used by the future tool loop

Acceptance criteria:
- backend returns the frozen mock shape
- citation normalizer handles `http`, `%7e`, and canonical URL cleanup
- API code does not assume the final retrieval implementation yet

Likely paths:
- `src/api/`
- `src/agent/`
- `src/config.py`
- `.env.example`

## Contributor C - Frontend and Eval Foundation

Primary outputs:
- single-page chat shell against mock data
- loading, error, refusal, and source display states
- initial golden dataset and eval scaffolding
- planning status upkeep

Acceptance criteria:
- the UI works entirely against mock responses
- source display matches the frozen citation object
- eval cases are versioned and human-readable

Likely paths:
- `frontend/`
- `data/eval/`
- `scripts/eval/`
- `docs/v0.1/README.md`

## Exit Criteria

- preprocessing artifacts are generated in the agreed shapes
- backend health and stub chat endpoints exist
- frontend renders the contract correctly against mocks
- the team can begin Sprint 2 without changing shared contracts
