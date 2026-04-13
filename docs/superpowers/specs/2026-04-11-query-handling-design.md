# Query Handling — Normalization & Cleanup
**Issue:** #23  
**Date:** 2026-04-11  
**Owner:** Contributor B (backend lane)  
**Branch:** `feat/b-query-normalization` (off `main`)

---

## Problem

Raw user queries sent to `POST /chat` degrade keyword search quality. Queries arrive with mixed case, stray punctuation, common filler phrases, and domain abbreviations (`fafsa`, `cpp`) that don't match the indexed text. The normalization layer cleans these before retrieval without touching the RAG pipeline internals.

---

## Decision: Where normalization lives

Normalization is inserted **inside `src/agent/tool_loop.py`**, just before the `search_corpus` call — not at the route level.

Reasons:
- The route (`routes.py`) handles HTTP concerns only; the agent owns retrieval logic.
- The LLM sees the raw user message (preserves conversational tone); retrieval sees the clean query (improves BM25 matching).
- Ambiguous-query short-circuit avoids the LLM call entirely, saving ~300–800 ms per rejected query.
- The eval harness and any future callers of `run_tool_loop()` inherit normalization automatically.

---

## File Structure

```
src/agent/
├── abbreviations.py        # NEW — ABBREVIATION_MAP constant dict
├── query_normalizer.py     # NEW — normalize() function + NormalizedQuery dataclass
├── tool_loop.py            # MODIFIED — calls normalize(), adds short-circuit path
└── system_prompt.py        # unchanged

tests/
└── test_query_normalizer.py   # NEW — unit tests for normalize()
```

No changes to `routes.py`, `models.py`, `settings.py`, or frontend.

---

## Data Types

```python
# src/agent/query_normalizer.py
from dataclasses import dataclass

@dataclass(frozen=True)
class NormalizedQuery:
    original: str          # raw user input, unchanged
    normalized_text: str   # cleaned, expanded query sent to retrieval
    is_ambiguous: bool     # True if < 3 tokens after cleanup
```

---

## Normalization Pipeline

Steps applied in order inside `normalize(raw: str) -> NormalizedQuery`:

1. **Strip whitespace** — `raw.strip()`
2. **Lowercase** — `.lower()`
3. **Strip filler phrases** — remove leading phrases (`"can you tell me"`, `"i want to know"`, `"i would like to know"`, `"could you tell me"`, `"please tell me"`) via regex
4. **Normalize punctuation** — collapse repeated `?!.,` to single; strip `?`, `!`, `"`, `'` at word boundaries
5. **Ambiguity check** — split on whitespace after step 4; `is_ambiguous = len(tokens) < 3`. Tokenization is `text.split()` (standard whitespace split — no external tokenizer dependency).
6. **Expand abbreviations** — token-by-token lookup against `ABBREVIATION_MAP`; replace matched tokens to produce `normalized_text`

> **Why ambiguity check precedes expansion (step 5 before step 6):** A query like `"cpp"` is 1 token and semantically under-specified even though it expands to "Cal Poly Pomona". Checking before expansion preserves the student's intent signal — if they typed one word, we ask for more context regardless of how the abbreviation expands.

---

## Abbreviation Map (seed)

```python
# src/agent/abbreviations.py
ABBREVIATION_MAP: dict[str, str] = {
    "cpp":   "Cal Poly Pomona",
    "fafsa": "Free Application for Federal Student Aid",
    "fa":    "financial aid",
    "cs":    "computer science",
    "ce":    "computer engineering",
    "ee":    "electrical engineering",
    "ime":   "industrial and manufacturing engineering",
    "rec":   "recreation center",
    "asi":   "associated students incorporated",
    "sa":    "student affairs",
    "dsp":   "disability services and programs",
    "eop":   "educational opportunity program",
    "irc":   "information resources and technology",
}
```

---

## tool_loop.py Integration

At the top of `run_tool_loop()`, before any LLM or retrieval call. The module-level logger is obtained via `logger = logging.getLogger(__name__)` (consistent with the existing pattern in `routes.py`):

```python
normalized = normalize(message)
logger.debug(
    "query raw=%r normalized=%r ambiguous=%s",
    normalized.original, normalized.normalized_text, normalized.is_ambiguous,
)

if normalized.is_ambiguous:
    return ChatResponse(
        conversation_id=cid,
        status=ChatStatus.NOT_FOUND,
        answer_markdown=(
            "Your question is a bit short — could you give me more detail? "
            "For example: *\"What are the FAFSA deadlines at CPP?\"* or "
            "*\"Where is the financial aid office?\"*"
        ),
        citations=[],
    )
```

Everywhere `message` was passed to retrieval, replace with `normalized.normalized_text`.

### Clarification response rationale
- `ChatStatus.NOT_FOUND` — agent didn't error, it needs more input. No HTTP 4xx.
- `answer_markdown` gives concrete examples so the student knows what to type next.
- `citations=[]` — no sources to cite for a clarification.
- LLM is **never called** on this path — full round-trip latency saved.

---

## Acceptance Criteria (from issue #23)

| Input | `normalized_text` | `is_ambiguous` | Note |
|---|---|---|---|
| `"  FAFSA DUE WHEN?? "` | `"free application for federal student aid due when"` | `False` | 5 tokens after normalization |
| `"cpp"` | `"Cal Poly Pomona"` | `True` → clarification returned | 1 pre-expansion token; ambiguity checked before expansion |
| `"hi"` | `"hi"` | `True` → clarification returned | 1 token, no expansion |

---

## Testing Plan

### `tests/test_query_normalizer.py` (new, unit)

| # | Test | Input | Assertion |
|---|---|---|---|
| 1 | Lowercase + strip whitespace | `"  FAFSA DUE WHEN?? "` | `normalized_text == "free application for federal student aid due when"` |
| 2 | Abbreviation expansion — multi-token query | `"cpp admissions"` | `normalized_text` starts with `"Cal Poly Pomona admissions"` |
| 3 | Filler phrase strip — leading phrase | `"can you tell me about parking"` | `normalized_text == "about parking"` (filler removed, content preserved) |
| 4 | Punctuation normalization — repeated marks | `"what is fafsa???"` | `"???"` not in `normalized_text` |
| 5 | Ambiguous — 1 pre-expansion token | `"cpp"` | `is_ambiguous=True` (checked before expansion) |
| 6 | Ambiguous — 2 pre-expansion tokens | `"fafsa deadline"` | `is_ambiguous=True` |
| 7 | Not ambiguous — 3 pre-expansion tokens | `"fafsa deadline cpp"` | `is_ambiguous=False` |
| 8 | Filler-only → empty after strip | `"can you tell me"` | `normalized_text == ""` and `is_ambiguous=True` (0 tokens → `< 3`) |
| 9 | Original field preserved unchanged | `"  FAFSA DUE WHEN?? "` | `normalized.original == "  FAFSA DUE WHEN?? "` |

### `tests/test_api.py` (additions to existing class)

- `test_chat_ambiguous_query_returns_clarification` — posts `"hi"`, asserts `status == "not_found"`, `answer_markdown` contains clarification text
- `test_chat_normalized_query_hits_retrieval` — posts `"  FAFSA DUE WHEN?? "`, asserts `status == "answered"`

### Coverage target
- `query_normalizer.py` — 100% (pure logic, all branches exercisable)
- `abbreviations.py` — data only, no coverage requirement

---

## Out of Scope (deferred)

- LLM-based query rewrite for heavily fragmented queries (stretch goal from issue)
- Persistent abbreviation map editable at runtime
- Per-user normalization preferences
