# V0.1 Implementation Plan

Last updated: 2026-04-05

## Summary

V0.1 is organized as four gated sprints so three contributors can work in parallel without colliding. The critical idea is contract-first planning: freeze interfaces, then split the team into data/retrieval, backend, and frontend/eval lanes.

## Sprint Overview

| Sprint | Goal | Parallelism | Exit Gate |
|---|---|---|---|
| Sprint 0 | Freeze contracts and handoff artifacts | Low | Shared schemas and fixtures are stable |
| Sprint 1 | Build foundations in three lanes | High | Cleaned corpus, backend skeleton, frontend on mocks |
| Sprint 2 | Integrate core end-to-end system | Medium | Full local app meets competition core requirements |
| Sprint 3 | Harden, rehearse, and add one showcase lane | Medium | Demo-ready build with no open core blockers |

## Sprint 0 - Contracts and Parallel Work Setup

Goal:
- remove ambiguity before implementation begins

Contributor A:
- define preprocessing outputs for cleaned files, metadata, and filter reports
- define discard reasons and page-quality flags
- document assumptions about redirect pages, login gates, hub pages, and duplicate boilerplate

Contributor B:
- define `POST /chat` schema
- define `search_corpus(query, top_k)` input and output contract
- define `Citation` object, refusal status, and error shape
- define `conversation_id` lifecycle

Contributor C:
- create mock response fixtures based on the contract
- create a thin 12-15 case golden set
- keep [README.md](./README.md) current as the source of truth

Shared:
- agree on black, ruff, isort, pytest config (Contributor B commits `pyproject.toml`)
- agree on eslint, prettier config (Contributor C commits frontend config)
- agree on branch naming convention (`feat/a-*`, `feat/b-*`, `feat/c-*`)
- agree on shared file ownership (see README)
- agree on PR merge rule (one non-author approval)

Deliverables:
- [sprint-0-contracts.md](./sprint-0-contracts.md)
- frozen mock fixtures
- initial golden set
- `pyproject.toml` with tooling config
- frontend linter/formatter config

## Sprint 1 - Foundation

Goal:
- let all three contributors work in parallel on isolated surfaces

Contributor A:
- implement structure-based preprocessing
- generate `data/cleaned/`, `data/metadata.json`, and `data/filter_report.json`
- validate boilerplate removal against representative files and tables

Contributor B:
- scaffold FastAPI app, `GET /health`, and stub `POST /chat`
- implement citation normalization helpers for `index.json`
- define retrieval interface so backend can integrate without waiting on full retrieval quality

Contributor C:
- build a single-page React chat shell against mock data
- implement message list, input, loading, error, refusal, and source display states
- keep planning docs and sprint status current

Deliverables:
- cleaned corpus artifacts
- working backend skeleton
- working frontend shell on mock data

## Sprint 2 - Core End-to-End

Goal:
- satisfy the competition core requirements locally from a cloned repo

Contributor A:
- implement heading-aware chunking
- ship BM25 first
- add semantic retrieval and hybrid fusion only if it improves the thin eval set

Contributor B:
- wire `search_corpus` into the tool loop
- implement system prompt, citation dedupe, refusal behavior, and multi-turn memory
- integrate retrieval into the real `/chat` path

Contributor C:
- swap frontend from mock to live API
- verify markdown, tables, citations, starter prompts, reset flow, and failure states
- expand the thin eval set as integration reveals misses

Deliverables:
- local end-to-end app
- grounded answers with source citations
- follow-up questions work within the same conversation

## Sprint 3 - Hardening and Showcase

Goal:
- remove demo risk first, then add one controlled showcase feature

Contributor A:
- tune retrieval only where the eval set shows misses
- add reranker only if recall remains below target after reasonable hybrid tuning

Contributor B:
- improve latency, caching, graceful failures, and startup flow
- finalize run command, `.env.example`, and integration stability

Contributor C:
- finalize demo flow, screenshots, and local setup documentation
- add one showcase feature only after core exit criteria are green
- preferred showcase: source provenance inspector, not analytics

Deliverables:
- reproducible demo run
- stable README and startup steps
- one optional showcase lane at most

## Shared Contracts

### Preprocessing outputs
- `data/cleaned/`: cleaned markdown per surviving source file
- `data/metadata.json`: canonical metadata per surviving page and chunk source
- `data/filter_report.json`: excluded files, discard reasons, and summary counts

### `POST /chat`
- Request:
  - `conversation_id` optional on first turn
  - `message` required
- Response:
  - `conversation_id`
  - `status`
  - `answer_markdown`
  - `citations[]`

### Citation object
- `title`
- `url`
- `snippet`

### `search_corpus`
- Input:
  - `query`
  - `top_k`
- Output items:
  - `chunk_id`
  - `title`
  - `url`
  - `snippet`
  - `score`

## Non-Negotiable Gates

- Do not start parallel implementation until Sprint 0 contracts are frozen.
- Do not start showcase work until Sprint 2 exit criteria pass.
- Do not broaden product scope during Sprint 3; only one showcase lane is allowed.
