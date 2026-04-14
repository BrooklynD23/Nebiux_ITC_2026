# Documentation Drift Report

Date: 2026-04-09 (updated 2026-04-12)

## Summary

The repo instructions and architecture docs were out of sync with the current preprocessing code layout. I updated the canonical instruction files and the docs that still referenced deleted notebook paths.

## Drift Found

1. The repo had `AGENTS.md` but no canonical `AGENT.md`, while several docs still pointed only at `CLAUDE.md`.
2. `docs/issue-18-setup-architecture.md` still referenced deleted `preprocessing_pipeline_test/` notebook and artifact paths.
3. The preprocessing consolidation spec described `freshness_manifest.json` and `conflict_review.md` as if the main pipeline already emitted them, but `scripts/preprocess/run_pipeline.py` still wrote only `data/cleaned/`, `data/metadata.json`, and `data/filter_report.json`.
4. The `scripts/preprocess/freshness.py` module docstring still referenced the deleted notebook path.

## Fixes Applied

- Added [`AGENT.md`](../AGENT.md) as the canonical Codex-facing instruction file.
- Converted [`AGENTS.md`](../AGENTS.md) into a compatibility shim.
- Updated [`CLAUDE.md`](../CLAUDE.md) and [`AGENT.md`](../AGENT.md) to match the current repo state and current preprocessing outputs.
- Updated [`docs/v0.1/README.md`](./v0.1/README.md) ownership entries to include `AGENT.md`.
- Updated [`docs/issue-18-setup-architecture.md`](./issue-18-setup-architecture.md) and the preprocessing consolidation spec to reflect the present code layout.
- Removed the stale notebook path from [`scripts/preprocess/freshness.py`](../scripts/preprocess/freshness.py).
- **Closed 2026-04-10:** `scripts/preprocess/run_pipeline.py` now writes `data/freshness_manifest.json` and `data/conflict_review.md` (commit `3f79472`), so the "Remaining Gap" below is resolved.

## Remaining Gap

- None — all items above are closed.

## 2026-04-12 Drift Follow-up

### Drift Found

1. Root `README.md` still described runtime conversation state as in-memory, but the merged backend now persists conversation turns in SQLite (`ConversationStore`).
2. Root `README.md` did not document the currently merged query-normalization behavior in the scaffolded `/chat` flow.

### Fixes Applied

- Updated [`README.md`](../README.md) storage decision to reflect SQLite-backed conversation persistence and configuration via `CONVERSATION_DB_PATH`.
- Updated [`README.md`](../README.md) repo status notes to include query normalization and ambiguous-query clarification behavior currently present in `src/agent/tool_loop.py`.

## 2026-04-13 Judge Docs Follow-up

### Drift Found

1. The root `README.md` did not point judges at the canonical competition docs up front.
2. The judge-facing deployment guide needed an explicit HTTPS note for voice accessibility so the hosted demo instructions matched the implemented UI behavior.

### Fixes Applied

- Updated [`README.md`](../README.md) to surface the judge entry points immediately.
- Updated [`docs/judging-and-deployment.md`](./judging-and-deployment.md) to document the current judge-facing host shape and the HTTPS requirement for microphone access.
- Kept [`docs/v0.1/README.md`](./v0.1/README.md) aligned as the active source of truth for the current sprint and showcase lane.
