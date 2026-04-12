# Documentation Drift Report

Date: 2026-04-09 (updated 2026-04-10)

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
