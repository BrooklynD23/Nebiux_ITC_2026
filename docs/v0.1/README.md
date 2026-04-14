# V0.1 Frozen Status

Last updated: 2026-04-14

This folder is the frozen handoff record for V0.1. It is no longer a sprint board.

## Final State

- The project is a web app, not a Chrome extension.
- The core stack is React + Vite frontend, FastAPI backend, and offline preprocessing/retrieval artifacts in `data/`.
- The competition flow centers on a single chat route with grounded answers, citations, multi-turn conversation, and the existing voice fallback path.
- The hosted demo path uses `docker-compose.hosted.yml` on a Google Cloud VM instance, with TLS handled outside the repo when HTTPS is required.
- The preprocessing pipeline already writes the production artifacts used by the repo: `data/cleaned/`, `data/metadata.json`, `data/filter_report.json`, `data/freshness_manifest.json`, and `data/conflict_review.md`.
- The issue #18 architecture decision is documented in [`docs/issue-18-setup-architecture.md`](../issue-18-setup-architecture.md).

## Frozen Scope

Keep:

- web app delivery
- one `search_corpus` tool
- preprocessing, retrieval, citations, refusal behavior, and multi-turn chat
- offline index and artifact generation

Defer or cut for V0.1:

- council-of-agents
- persistent student profile
- multilingual support beyond the English-first demo
- mascot widget and extra surface area
- specialized tools beyond `search_corpus`

## Handoff Notes

- Local development is documented in [`README.md`](../../README.md).
- Deployment guidance is documented in [`docs/judging-and-deployment.md`](../judging-and-deployment.md).
- Shared repo instructions for agents live in [`CLAUDE.md`](../../CLAUDE.md) and [`AGENT.md`](../../AGENT.md).

## Reference Paths

- [Implementation plan](./implementation-plan.md)
- [Issue #18 setup architecture](../issue-18-setup-architecture.md)
- [Judging and deployment guide](../judging-and-deployment.md)
