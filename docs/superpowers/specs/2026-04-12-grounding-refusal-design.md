# Grounding & Refusal Logic — Prevent Hallucination

**Issue:** [#21](https://github.com/BrooklynD23/Nebiux_ITC_2026/issues/21)
**Date:** 2026-04-12
**Owner:** Contributor B (backend lane)
**Status:** Revised after audit

---

## Context

The competition prompt requires: *"When the answer is not found, the agent should say so rather than hallucinate."* This is scored under **Implemented Features and Functionality (30 pts)**.

Currently the tool loop is stubbed with keyword-routed responses. Another team is building the RAG pipeline (simple BM25, expanding to hybrid if time permits). This design delivers a **self-contained grounding/refusal layer** that plugs into whatever retrieval backend ships, without coupling to the LLM provider or retrieval implementation.

The layer answers one question: *"Are the search results strong enough to attempt an answer?"*

---

## Approach

**Pure Function Layer** — a single `src/agent/grounding.py` module containing:
- `assess_confidence()` — evaluates search results against configurable thresholds
- `build_refusal_response()` — constructs a standardized refusal `ChatResponse`
- `PostHocValidator` protocol + `NoOpValidator` skeleton for future chunk-vs-answer verification

No retriever wrapping, no pipeline abstraction. The caller (tool_loop) invokes `assess_confidence()` with search results and acts on the verdict.

---

## Data Models

### GroundingVerdict

Immutable dataclass returned by `assess_confidence()`.

```python
@dataclass(frozen=True)
class GroundingVerdict:
    grounded: bool           # True if retrieval confidence meets threshold
    confidence_score: float  # Aggregate score (0.0-1.0)
    reason: str              # Human-readable explanation
```

### ScoreAggregation

Type-safe enum for aggregation mode (prevents silent typo bugs):

```python
from typing import Literal

ScoreAggregation = Literal["max", "mean_top3", "count_only"]
```

### GroundingConfig

Immutable dataclass for threshold tuning.

```python
@dataclass(frozen=True)
class GroundingConfig:
    min_top_score: float = 0.3                          # Minimum score of best result
    min_results: int = 1                                # Minimum qualifying results
    score_aggregation: ScoreAggregation = "max"         # Type-safe aggregation mode
    expected_top_k: int = 5                             # Used as divisor in count_only mode
```

- `"max"` — confidence = highest score among all results.
- `"mean_top3"` — confidence = mean of top 3 scores.
- `"count_only"` — skip score filtering, only check result count. Confidence = `min(1.0, len(results) / expected_top_k)`. Useful when RAG team's scores aren't normalized yet.

**Note:** `expected_top_k` should match the `top_k` parameter passed to `RetrieverBase.search_corpus()` so count-only confidence scales correctly.

### ChatResponse Contract

No public API schema change in this phase.

`ChatResponse` remains:

```python
class ChatResponse(BaseModel):
    conversation_id: str
    status: ChatStatus
    answer_markdown: str
    citations: list[Citation] = []
```

Grounding verdict values (`grounded`, `confidence_score`, detailed reason) are internal-only for tool-loop control and logs.

---

## Core Logic

### assess_confidence()

**File:** `src/agent/grounding.py`

```python
def assess_confidence(
    results: list[SearchResult],
    config: GroundingConfig = GroundingConfig(),
) -> GroundingVerdict:
```

**Algorithm:**

1. **Empty check:** If `results` is empty, return `GroundingVerdict(grounded=False, confidence_score=0.0, reason="no results returned")`.

2. **Count-only mode:** If `config.score_aggregation == "count_only"`:
   - Confidence = `min(1.0, len(results) / config.expected_top_k)`.
   - If `len(results) >= config.min_results`: grounded.
   - Otherwise: not grounded.
   - Skip steps 3-5.

3. **Filter qualifying results:** Keep results where `score >= config.min_top_score`.

4. **Count check:** If `len(qualifying) < config.min_results`, return not grounded. Confidence = max score across all results (not just qualifying).

5. **Compute confidence:**
   - `"max"`: `max(r.score for r in results)`
   - `"mean_top3"`: mean of top 3 scores (or all if fewer than 3)
   - Any other value: raise `ValueError(f"Unknown aggregation mode: {config.score_aggregation}")`. (The `Literal` type prevents this at type-check time, but the runtime guard catches dynamic misuse.)

6. **Return:** `GroundingVerdict(grounded=True, confidence_score=computed, reason="passed")`.

### build_refusal_response()

```python
def build_refusal_response(
    conversation_id: str,
    verdict: GroundingVerdict,
    context: RefusalContext,
) -> ChatResponse:
    query = context.normalized_query
    return ChatResponse(
        conversation_id=conversation_id,
        status=ChatStatus.NOT_FOUND,
        answer_markdown=(
            "I couldn't find enough reliable information on the CPP website "
            f'for "{query}". Please check [cpp.edu](https://www.cpp.edu) '
            "directly or contact the relevant office."
        ),
        citations=[],
    )
```

---

## Post-Hoc Validation Skeleton

Protocol and no-op implementation for future chunk-vs-answer verification.

```python
class PostHocValidator(Protocol):
    def validate(
        self, answer: str, chunks: list[SearchResult]
    ) -> GroundingVerdict:
        """Check if the LLM's answer is grounded in the retrieved chunks.

        Future implementations could:
        - Compute keyword overlap ratio between answer and chunks
        - Use an LLM-as-judge call to verify entailment
        - Check that cited URLs match returned chunk URLs
        """
        ...

class NoOpValidator:
    """Placeholder that always passes. Replace with real validation when ready."""

    def validate(
        self, answer: str, chunks: list[SearchResult]
    ) -> GroundingVerdict:
        return GroundingVerdict(
            grounded=True,
            confidence_score=1.0,
            reason="post-hoc validation not implemented",
        )
```

---

## Integration

### Where it plugs in

**File:** `src/agent/tool_loop.py`

Current flow:
```
normalize → ambiguity check → [stub response]
```

Updated flow (for RAG team to wire):
```
normalize → ambiguity check → [retrieve] → assess_confidence →
  if not grounded: build_refusal_response() → return (skip LLM)
  if grounded:     [LLM generates answer] → return ChatResponse(grounded=True, confidence_score=...)
```

When grounding fails, the LLM call is **skipped entirely**. This saves cost/latency and makes hallucination on weak results impossible.

### What the RAG team needs to do

1. Import `assess_confidence`, `build_refusal_response`, `GroundingConfig` from `src.agent.grounding`
2. After calling `search_corpus()`, pass results to `assess_confidence(results, config)`
3. If `verdict.grounded is False`, return `build_refusal_response(cid, verdict, context)`
4. If grounded, pass results to LLM and return the existing `ChatResponse` contract

### Stub integration (immediate)

For the current stub tool loop, ambiguous-input clarification stays a separate branch and does not run retrieval.

### Status semantics: `NOT_FOUND` with explicit internal reason

`ChatStatus.NOT_FOUND` is reused for both:
- ambiguous query clarification
- weak-retrieval refusal

These are intentionally tracked as separate internal causes (`ambiguous_query` vs. `weak_retrieval`) and **not inferred from confidence score**.

### Note on `conversation_id` types

`ChatRequest.conversation_id` is `Optional[uuid.UUID]`; the tool loop converts it to `str` before passing to `build_refusal_response()`. Implementers should always pass `str`, not `uuid.UUID`, to grounding functions.

---

## Configuration

**File:** `src/settings.py`

Add these fields to the `Settings` class following the existing `pydantic_settings` pattern:

```python
# Grounding thresholds
grounding_min_top_score: float = Field(
    default=0.3, alias="GROUNDING_MIN_TOP_SCORE"
)
grounding_min_results: int = Field(
    default=1, alias="GROUNDING_MIN_RESULTS"
)
grounding_score_aggregation: ScoreAggregation = Field(
    default="max", alias="GROUNDING_SCORE_AGGREGATION"
)
grounding_expected_top_k: int = Field(
    default=5, alias="GROUNDING_EXPECTED_TOP_K"
)

@property
def grounding_config(self) -> GroundingConfig:
    """Construct GroundingConfig from settings fields."""
    return GroundingConfig(
        min_top_score=self.grounding_min_top_score,
        min_results=self.grounding_min_results,
        score_aggregation=self.grounding_score_aggregation,
        expected_top_k=self.grounding_expected_top_k,
    )
```

| Variable | Default | Description |
|----------|---------|-------------|
| `GROUNDING_MIN_TOP_SCORE` | `0.3` | Minimum score for the best result |
| `GROUNDING_MIN_RESULTS` | `1` | Minimum qualifying results |
| `GROUNDING_SCORE_AGGREGATION` | `max` | `"max"`, `"mean_top3"`, or `"count_only"` |
| `GROUNDING_EXPECTED_TOP_K` | `5` | Divisor for count_only confidence (should match retriever top_k) |

The tool loop uses `get_settings().grounding_config` to get a `GroundingConfig` instance.

---

## Files to Create/Modify

| Action | File | Description |
|--------|------|-------------|
| **Create** | `src/agent/grounding.py` | Core grounding module |
| **Create** | `tests/test_grounding.py` | Unit tests |
| **No change** | `src/models.py` | Keep frozen Sprint 0 `ChatResponse` schema |
| **Modify** | `src/settings.py` | Add grounding threshold env vars |
| **Modify** | `src/agent/tool_loop.py` | Wire weak-retrieval refusal path while keeping ambiguity path separate |
| **Modify** | `docs/v0.1/README.md` | Mark as outdated / update stale references |
| **Modify** | `CLAUDE.md` | Remove stale v0.1 sprint references |

---

## Test Plan

**File:** `tests/test_grounding.py`

### Unit tests (`tests/test_grounding.py`)

Pure-function tests. No LLM, no database, no async required.

| # | Test Case | Input | Expected |
|---|-----------|-------|----------|
| 1 | Empty results | `[]` | `grounded=False, score=0.0` |
| 2 | Single low-score result | `[score=0.1]` | `grounded=False, score=0.1` |
| 3 | Single high-score result | `[score=0.8]` | `grounded=True, score=0.8` |
| 4 | Multiple results, none qualifying | `[0.1, 0.2, 0.15]` | `grounded=False, score=0.2` |
| 5 | Multiple results, some qualifying | `[0.8, 0.6, 0.1]` | `grounded=True, score=0.8` |
| 6 | Count-only mode, sufficient results | 3 results, `expected_top_k=5` | `grounded=True, score=0.6` |
| 7 | Count-only mode, empty | `[]` | `grounded=False, score=0.0` |
| 8 | Custom threshold rejects | `min_top_score=0.9`, best=0.85 | `grounded=False` |
| 9 | mean_top3 aggregation | `[0.9, 0.8, 0.7, 0.1]` | `score=0.8` |
| 10 | Refusal response shape | verdict `grounded=False` | correct ChatResponse |
| 11 | NoOpValidator always passes | any input | `grounded=True` |
| 12 | Invalid aggregation raises ValueError | `score_aggregation="bad"` | `ValueError` |
| 13 | count_only scales with expected_top_k | 3 results, `expected_top_k=10` | `score=0.3` |

### Integration test (`tests/test_tool_loop_grounding.py`)

| # | Test Case | Input | Expected |
|---|-----------|-------|----------|
| 14 | Tool-loop integration: weak retrieval refusal | non-ambiguous query + empty retrieval | `status=not_found` with refusal text including searched query |

---

## Verification

1. **Unit tests pass:** `pytest tests/test_grounding.py -v`
2. **Existing tests unbroken:** `pytest` (new ChatResponse defaults keep all passing)
3. **API contract unchanged:** `POST /chat` response still matches Sprint 0 schema
4. **Manual smoke test (ambiguity):** Send an ambiguous query via curl; verify clarification response
5. **Manual smoke test (weak retrieval):** Force empty retrieval and verify refusal mentions searched query

---

## Out of Scope

- Real LLM + tool calling integration (RAG team)
- Post-hoc validation implementation (future issue)
- Frontend display of confidence/grounding status
- Analytics dashboard for refusal rates
