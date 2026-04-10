# Preprocessing Pipeline Consolidation — Design Spec

**Date:** 2026-04-09
**Issue:** GitHub #18 (Setup Architecture) — preprocessing consolidation thread
**Status:** Approved

> Current implementation note: `scripts/preprocess/freshness.py`, `scripts/preprocess/conflicts.py`, and their tests now exist in the production tree, but `scripts/preprocess/run_pipeline.py` still emits only `data/cleaned/`, `data/metadata.json`, and `data/filter_report.json`. The freshness/conflict artifact wiring described below remains the next integration step.

## Problem

Two preprocessing pipelines exist with diverging capabilities:

1. **Production** (`scripts/preprocess/`) — modular (4 files, ~1,300 LOC), does core cleaning only (boilerplate stripping, filtering, metadata extraction). Outputs to `data/`.
2. **Notebook** (`preprocessing_pipeline_test/`) — monolithic (988 LOC), adds freshness scoring and conflict detection. Outputs to `pp_out/`.

Both produce 7,388 clean files from the 8,042 raw corpus files. The notebook pipeline also generates `freshness_manifest.json` (per-document risk scores) and `conflict_review.md` (59 conflict clusters across 338 files) — valuable for RAG quality but missing from the production path.

## Decision

Merge freshness and conflict detection into the production `scripts/preprocess/` modules. Delete `preprocessing_pipeline_test/` and `pp_out/`. Re-run the upgraded pipeline to regenerate all artifacts into `data/`.

## Architecture

### Module Structure

```
scripts/preprocess/
├── __init__.py           (existing — unchanged)
├── strip_boilerplate.py  (existing — unchanged, ~357 LOC)
├── filter_corpus.py      (existing — unchanged, ~198 LOC)
├── extract_metadata.py   (existing — unchanged, ~164 LOC)
├── freshness.py          (NEW, ~270 LOC)
├── conflicts.py          (NEW, ~120 LOC)
└── run_pipeline.py       (existing — extended, ~350 LOC)
```

### Pipeline Steps

1. Load raw corpus + URL index
2. Strip boilerplate (`strip_boilerplate.py`)
3. Filter & extract metadata (`filter_corpus.py` + `extract_metadata.py`)
4. **Freshness scoring** (`freshness.py`) — compute per-document risk scores
5. **Conflict detection** (`conflicts.py`) — identify conflicting document clusters
6. Write cleaned files + all artifacts to `data/`

### Output Artifacts

| Artifact | Path | Description |
|----------|------|-------------|
| Cleaned markdown | `data/cleaned/` | 7,388 surviving corpus files |
| Page metadata | `data/metadata.json` | Per-page metadata array |
| Filter report | `data/filter_report.json` | Excluded files with reasons |
| Freshness manifest | `data/freshness_manifest.json` | **NEW** — per-document risk scores (low/medium/high) |
| Conflict review | `data/conflict_review.md` | **NEW** — human-readable conflict cluster report |

## Module Details

### `freshness.py`

Ported from the archived notebook pipeline used for this issue (321 LOC). Estimated ~270 LOC after splitting out conflicts.

**Exports:**

```python
def collect_document_metadata(
    *,
    filename: str,
    source_url: str,
    cleaned_body: str,
    filter_result: FilterResult,   # from filter_corpus.py — provides category, is_duplicate, duplicate_group_size
    alias_count: int,              # computed in run_pipeline from url_map reverse lookup
    file_mtime_iso: str,           # from os.stat() on the source file
) -> dict[str, Any]: ...

def compute_outdated_risk(
    metadata: dict[str, Any],
    *,
    cluster_context: dict[str, Any] | None = None,
) -> dict[str, Any]: ...

def build_topic_key(source_url: str, title: str) -> str: ...
```

**Parameter sourcing (H1/H2/H6 resolution):**
- `category` and `is_duplicate` — the current `FilterResult` (in `filter_corpus.py`) only has `keep: bool` and `reason: Optional[DiscardReason]`. **We must extend `FilterResult`** to add `category: str` (derived from the discard reason or "kept"), `is_duplicate: bool`, and `duplicate_group_size: int`. The `filter_page()` function and its callers will be updated to populate these fields. See `filter_corpus.py` changes below.
- `alias_count` — computed in `run_pipeline.py` by counting entries in the pre-computed reverse URL map (`file_to_urls`).
- `file_mtime_iso` — obtained via `os.stat(source_path).st_mtime` converted to ISO format. Added to the pipeline loop.
- `cleaned_body` — already available in the pipeline loop after boilerplate stripping.
- The original notebook parameter `body` (raw content) is dropped; freshness scoring only needs `cleaned_body`.

**Risk factors scored:**
- Legacy URL tokens (+3)
- Stale language phrases (+3)
- Redirect language (+2)
- Thin content <500 chars (+1)
- Duplicate group member (+1)
- Older than cluster peer (+2 or +3 depending on gap)
- Old explicit year (+1)
- Conflicting cluster membership (+2)

**Title extraction (H3 resolution):** The notebook's `_extract_title()` is more robust than the production version (handles link-only lines, filters generic titles like "cpp news", skips "search" lines, cleans inline links). We will **upgrade `extract_metadata._extract_title()`** to match the notebook's version, then have both `extract_metadata.py` and `freshness.py` use the same function. This requires regression testing of `data/metadata.json` output — title values may change for some documents, which is acceptable since the notebook version is more correct.

### `filter_corpus.py` Changes (H6 resolution)

Extend `FilterResult` dataclass to include fields needed by freshness scoring:

```python
@dataclass
class FilterResult:
    keep: bool
    reason: DiscardReason | None = None
    category: str = "kept"           # NEW — "redirect", "stub", "nav_heavy", "duplicate", "kept"
    is_duplicate: bool = False       # NEW
    duplicate_group_size: int = 1    # NEW
```

The `filter_page()` function will set `category` based on the discard reason (mapping `DiscardReason` enum values to category strings). Duplicate detection requires `run_pipeline.py` to do a content-hash pass before calling `filter_page()` and pass `is_duplicate`/`duplicate_group_size` into the result. This mirrors the notebook pipeline's approach where deduplication happens at the pipeline level, not inside the filter function.

### `conflicts.py`

Extracted from `detect_cluster_conflicts()` in `corpus_freshness.py`.

**Exports:**
- `detect_cluster_conflicts(records)` — groups kept documents by `topic_key`, finds clusters with diverging values across: `latest_year`, `contact_emails`, `contact_phones`, `money_amounts`, `date_mentions`. Identifies "newer candidate" per cluster.
- `format_conflict_report(clusters, stats)` — generates `conflict_review.md` markdown

### `run_pipeline.py` Changes

- Import `freshness` and `conflicts` modules
- **Pre-compute reverse URL map** once at startup: `file_to_urls: dict[str, list[str]]` from the URL index. This provides both `source_url` (first URL for each file) and `alias_count` (length of the URL list). Fixes the O(n) per-file reverse lookup (H5).
- After metadata extraction, call `collect_document_metadata()` for each kept file, passing `source_url` from the pre-computed `file_to_urls` map and `filter_result` from the existing filter step
- Call `detect_cluster_conflicts()` on the full metadata list
- Call `compute_outdated_risk()` per document with cluster context
- Write `data/freshness_manifest.json` and `data/conflict_review.md`
- Update summary report with freshness/conflict statistics (risk level distribution, cluster counts)

### `settings.py` Changes (H4 resolution)

Add two new properties to the `Settings` class, following the existing pattern:

```python
freshness_manifest_path: Path = DATA_DIR / "freshness_manifest.json"
conflict_review_path: Path = DATA_DIR / "conflict_review.md"
```

Update `health` endpoint in `src/api/main.py` to report freshness/conflict artifact readiness alongside existing checks.

## Cleanup

**Delete:**
- `preprocessing_pipeline_test/` — entire directory
- `pp_out/` — pipeline output directory

**Add to `.gitignore`:**
- `data/cleaned/`
- `data/freshness_manifest.json`
- `data/conflict_review.md`
- `pp_out/`

**Update `CLAUDE.md` and `AGENT.md`:** Note the current preprocessing outputs and the fact that freshness/conflict artifacts are not yet emitted by `run_pipeline.py`.

## Testing

### New Test Files

- `tests/test_freshness.py` — unit tests for `compute_outdated_risk()` with various risk combinations, `collect_document_metadata()` output shape
- `tests/test_conflicts.py` — unit tests for `detect_cluster_conflicts()` with mock records, `format_conflict_report()` output

### Validation

1. Lint: `ruff check scripts/preprocess/freshness.py scripts/preprocess/conflicts.py`
2. Tests: `pytest tests/test_freshness.py tests/test_conflicts.py`
3. Full pipeline run: `python scripts/preprocess/run_pipeline.py` — verify all 5 artifacts in `data/`
4. Downstream: `python scripts/build_index.py` — verify index build against `data/cleaned/`
5. Full test suite: `pytest` — all existing tests still pass

## Out of Scope

- Retrieval wiring (BM25/semantic retriever implementations) — separate issue
- ChromaDB/sentence-transformers integration — deferred to retrieval issue
- Tool loop replacement — deferred to retrieval issue
- Using freshness data at retrieval time — deferred to retrieval issue (but the manifest will be ready)
