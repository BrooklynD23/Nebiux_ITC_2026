# System Architecture Document
## Nebiux ITC 2026 — CPP Campus Knowledge Agent

**Version:** V0.1 (Frozen Handoff)
**Date:** 2026-04-14
**Project:** Cal Poly Pomona Intelligent Campus Assistant

---

## Table of Contents

1. [System Overview & Design Principles](#1-system-overview--design-principles)
2. [Architecture Diagram](#2-architecture-diagram)
3. [Data Pipeline](#3-data-pipeline)
4. [Retrieval Engine](#4-retrieval-engine)
5. [AI Agent Loop](#5-ai-agent-loop)
6. [API Layer](#6-api-layer)
7. [Frontend](#7-frontend)
8. [Testing & Evaluation](#8-testing--evaluation)
9. [Deployment & Setup](#9-deployment--setup)
10. [Tech Stack Reference](#10-tech-stack-reference)

---

## 1. System Overview & Design Principles

### What It Does

The CPP Campus Knowledge Agent is a Retrieval-Augmented Generation (RAG) chatbot scoped exclusively to Cal Poly Pomona. Students can ask questions about admissions, academics, campus services, and student life. The system finds relevant documents from a preprocessed CPP corpus, grounds all answers in that evidence, and returns cited, markdown-formatted responses.

### Core Design Principles

| Principle | Implementation |
|---|---|
| **Grounding over generation** | LLM never answers without first calling `search_corpus`. Weak retrieval triggers an immediate refusal — not a hallucinated answer. |
| **Safety before LLM** | Urgent queries (mental health, medical, police, financial hardship) are routed deterministically with no LLM involvement. |
| **Graceful degradation** | Hybrid retrieval falls back to BM25-only if the vector index is unavailable. API returns 503 for retrieval and transcription failures rather than silent errors. |
| **Full auditability** | Every conversation turn is persisted to SQLite (message, citations, normalized query, retrieved chunks, token counts). Admin routes expose this for review. |
| **Provider portability** | The same system prompt and agentic loop works against both Gemini and OpenAI. Provider-specific tool-calling protocol is isolated to `_gemini_loop` and `_openai_loop`. |
| **Offline-first corpus** | The corpus is preprocessed and indexed at build time, not at query time. Startup auto-builds artifacts if missing. |
| **Scope enforcement** | Query normalization + system prompt + grounding thresholds work in layers to reject out-of-scope queries before fabrication can occur. |

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             USER BROWSER                                    │
│                                                                             │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │                    React + Vite Frontend (port 5173)                 │  │
│   │                                                                      │  │
│   │  ┌────────────┐  ┌─────────────────┐  ┌──────────────────────────┐  │  │
│   │  │  useChat   │  │  useVoiceInput  │  │   Admin Dashboard View   │  │  │
│   │  │    hook    │  │      hook       │  │   (GET /admin/*)         │  │  │
│   │  └─────┬──────┘  └────────┬────────┘  └──────────────────────────┘  │  │
│   │        │                  │                                           │  │
│   │  ┌─────▼──────────────────▼────────────────────────────────────┐    │  │
│   │  │                   api/client.ts                             │    │  │
│   │  │  sendMessage()  ·  transcribeAudio()  ·  fetchAdmin*()     │    │  │
│   │  └──────────────────────────┬──────────────────────────────────┘    │  │
│   └─────────────────────────────┼────────────────────────────────────────┘  │
└─────────────────────────────────┼─────────────────────────────────────────────┘
                    HTTP (proxied via Vite dev / Nginx prod)
                                  │
┌─────────────────────────────────▼─────────────────────────────────────────────┐
│                           FastAPI Backend (port 8000)                          │
│                                                                                │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ POST /chat   │  │ POST /transcribe  │  │ GET /health  │  │ GET /admin/* │  │
│  │  routes.py   │  │   routes.py      │  │  main.py     │  │  admin.py    │  │
│  └──────┬───────┘  └────────┬─────────┘  └──────────────┘  └──────┬───────┘  │
│         │                   │                                        │          │
│         │            ┌──────▼──────┐                        ┌───────▼──────┐  │
│         │            │ OpenAI      │                        │ Conversation │  │
│         │            │ Whisper API │                        │   Store      │  │
│         │            │(transcribe) │                        │ (SQLite)     │  │
│         │            └─────────────┘                        └──────────────┘  │
│         │                                                                      │
│  ┌──────▼─────────────────────────────────────────────────────────────────┐   │
│  │                         Agent Tool Loop (src/agent/)                   │   │
│  │                                                                        │   │
│  │  1. QueryNormalizer ──────────────────────────────────────────────     │   │
│  │     • strip filler, expand abbreviations, detect ambiguity            │   │
│  │                                                                        │   │
│  │  2. SupportRouter ────────────────────────────────────────────────     │   │
│  │     • regex match → police / health / mental health / financial       │   │
│  │     • if urgent: fetch chunks, return deterministic response (no LLM) │   │
│  │                                                                        │   │
│  │  3. LLM Provider Loop ─────────────────────────────────────────────    │   │
│  │     ┌──────────────────┐       ┌──────────────────────────────┐       │   │
│  │     │  _gemini_loop()  │  OR   │       _openai_loop()         │       │   │
│  │     │  gemini-2.5-flash│       │       gpt-4o-mini            │       │   │
│  │     └────────┬─────────┘       └───────────────┬──────────────┘       │   │
│  │              │                                  │                      │   │
│  │              └──────────────┬───────────────────┘                      │   │
│  │                             │ tool_call: search_corpus(query, top_k)   │   │
│  │                             │                                          │   │
│  │  4. GroundingCheck ─────────┼─────────────────────────────────────     │   │
│  │     assess_confidence() ← first retrieval result                      │   │
│  │     score < 0.3 → refusal response (skip LLM completion)              │   │
│  │                             │                                          │   │
│  │  5. CitationExtractor ──────┘──────────────────────────────────────    │   │
│  │     footer parse → text match fallback → dedup by URL                │   │
│  │                                                                        │   │
│  └──────────────────────────┬─────────────────────────────────────────────┘  │
│                             │ search_corpus()                                  │
│  ┌──────────────────────────▼─────────────────────────────────────────────┐   │
│  │                    Hybrid Retriever (src/retrieval/)                   │   │
│  │                                                                        │   │
│  │   ┌────────────────────────┐      ┌────────────────────────────────┐  │   │
│  │   │   ChromaRetriever      │      │       WhooshRetriever          │  │   │
│  │   │   (semantic search)    │      │       (BM25 lexical search)    │  │   │
│  │   │                        │      │                                │  │   │
│  │   │  all-MiniLM-L6-v2      │      │  Multifield: content,         │  │   │
│  │   │  384-dim embeddings    │      │  title, heading               │  │   │
│  │   │  cosine similarity     │      │  Normalized BM25 score        │  │   │
│  │   └──────────┬─────────────┘      └──────────────┬────────────────┘  │   │
│  │              │                                    │                   │   │
│  │              └──────────────┬─────────────────────┘                   │   │
│  │                             │ RRF Fusion (k=60)                       │   │
│  │                             ▼                                         │   │
│  │                    top_k SearchResults                                │   │
│  │              { chunk_id, title, url, snippet, score }                │   │
│  └────────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────────┘
                                        │
        ┌───────────────────────────────┼───────────────────────────────┐
        │                    Persisted Artifacts (data/)                │
        │                                                               │
        │  ┌──────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
        │  │ chunks.jsonl │  │ indexes/whoosh/ │  │ indexes/chroma/ │  │
        │  │ 91,407 chunks│  │  BM25 index     │  │  Vector index   │  │
        │  └──────────────┘  └─────────────────┘  └─────────────────┘  │
        │  ┌──────────────┐  ┌─────────────────┐                        │
        │  │ cleaned/     │  │conversations.db │                        │
        │  │ 7,398 docs   │  │  SQLite (WAL)   │                        │
        │  └──────────────┘  └─────────────────┘                        │
        └───────────────────────────────────────────────────────────────┘
                                        │
        ┌───────────────────────────────▼───────────────────────────────┐
        │             Offline Data Pipeline (scripts/)                  │
        │                                                               │
        │  dataset/itc2026_ai_corpus/  ──►  run_pipeline.py            │
        │    (raw HTML/markdown)           strip_boilerplate            │
        │                                  extract_metadata             │
        │                                  filter_corpus                │
        │                                  conflicts                    │
        │                                  freshness                    │
        │                             ──►  data/cleaned/                │
        │                             ──►  build_index.py               │
        │                             ──►  chunks.jsonl + indexes       │
        └───────────────────────────────────────────────────────────────┘
```

---

## 3. Data Pipeline

The data pipeline is a one-time offline process. It transforms a raw HTML/markdown corpus into structured, indexed, retrieval-ready artifacts. It runs automatically on first container startup (if `AUTO_BUILD_ARTIFACTS=true`) and is idempotent.

### 3.1 Pipeline Stages

```
RAW CORPUS (dataset/itc2026_ai_corpus/)
          │
          ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Stage 1: strip_boilerplate.py                                       │
│  Input:  Raw HTML / markdown files                                   │
│  Output: Text with HTML tags, CSS, JS, nav elements removed          │
│  Goal:   Reduce noise before NLP processing                          │
└──────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Stage 2: extract_metadata.py                                        │
│  Input:  Boilerplate-stripped documents                              │
│  Output: data/metadata.json (title, URL, last-modified per doc)      │
│  Goal:   Capture document-level attributes for citation generation   │
└──────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Stage 3: filter_corpus.py                                           │
│  Input:  All cleaned candidates                                      │
│  Output: data/cleaned/ (kept docs) + data/filter_report.json        │
│  Goal:   Remove near-duplicates, off-topic pages, low-quality docs   │
└──────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Stage 4: conflicts.py                                               │
│  Input:  Cleaned corpus                                              │
│  Output: data/conflict_review.md (human-readable report)             │
│  Goal:   Flag pages with contradictory info (e.g., duplicate dates)  │
└──────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Stage 5: freshness.py                                               │
│  Input:  Cleaned corpus + metadata                                   │
│  Output: data/freshness_manifest.json (staleness risk per doc)       │
│  Goal:   Flag old or undated documents for manual review             │
└──────────────────────────────────────────────────────────────────────┘
          │
          ▼
    data/cleaned/
    7,398 markdown documents
          │
          ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Index Build: build_index.py                                         │
│                                                                      │
│  Step 1: Read cleaned markdown files                                 │
│  Step 2: Split into heading-aware chunks                             │
│          - Primary split: markdown headings (#, ##, ###)             │
│          - Secondary split: paragraphs (max 1,400 chars/chunk)       │
│          - Prefix each chunk with section heading for context        │
│  Step 3: Write data/chunks.jsonl (91,407 chunks total)               │
│          Each chunk: { chunk_id, source_file, title, url, heading,   │
│                        content, snippet, word_count }               │
│  Step 4: Build Whoosh BM25 index at data/indexes/whoosh/            │
│          - Schema fields: ID (stored), title (stored, text),         │
│            url (stored), chunk_id (stored), content (text),          │
│            heading (text)                                            │
│  Step 5: Build Chroma vector index at data/indexes/chroma/          │
│          - Embed chunks using all-MiniLM-L6-v2 (384-dim)            │
│          - Persist as Chroma collection "cpp_corpus"                 │
└──────────────────────────────────────────────────────────────────────┘
          │
          ▼
    ┌─────────────────────────────────┐
    │  data/indexes/whoosh/           │  ← BM25 index (Whoosh)
    │  data/indexes/chroma/           │  ← Vector index (Chroma + SQLite)
    │  data/chunks.jsonl              │  ← Chunk manifest
    │  data/metadata.json             │  ← Document metadata
    │  data/filter_report.json        │  ← Filtering audit log
    │  data/freshness_manifest.json   │  ← Freshness risk report
    │  data/conflict_review.md        │  ← Conflict report
    └─────────────────────────────────┘
```

### 3.2 Corpus Statistics

| Artifact | Count |
|---|---|
| Raw corpus files | Input dataset |
| Cleaned documents | 7,398 |
| Retrieval chunks | 91,407 |
| Max chunk size | 1,400 characters |
| Embedding model | all-MiniLM-L6-v2 (384-dim) |

### 3.3 Chunk Format (chunks.jsonl)

```json
{
  "chunk_id": "abc123-def456",
  "source_file": "cleaned/academic-calendar.md",
  "title": "Academic Calendar | Cal Poly Pomona",
  "url": "https://www.cpp.edu/registrar/academic-calendar.shtml",
  "heading": "Fall 2025 Dates",
  "content": "Fall 2025 Dates\n\nInstruction begins: August 25, 2025...",
  "snippet": "Instruction begins August 25, 2025...",
  "word_count": 87
}
```

---

## 4. Retrieval Engine

### 4.1 Architecture Overview

The retrieval layer is a hybrid system combining BM25 lexical search (Whoosh) and dense semantic search (Chroma), fused using Reciprocal Rank Fusion (RRF). All backends implement the same abstract interface.

```python
class RetrieverBase(ABC):
    async def search_corpus(query: str, top_k: int = 5) -> list[SearchResult]
```

### 4.2 Backend: Whoosh BM25 (`src/retrieval/whoosh_retriever.py`)

- **Algorithm**: BM25 (Best Match 25) — probabilistic term frequency model
- **Index location**: `data/indexes/whoosh/`
- **Indexed fields**: `content`, `title`, `heading` (multifield OR query)
- **Score normalization**: `min(hit.score / top_score, 1.0)`
- **Snippet retrieval**: Loads from `chunks.jsonl` by `chunk_id`
- **Strengths**: Exact keyword match, acronyms, proper nouns, course codes
- **Weaknesses**: Fails on paraphrases, synonyms, semantic meaning

### 4.3 Backend: Chroma Semantic Search (`src/retrieval/chroma_retriever.py`)

- **Algorithm**: Approximate nearest neighbor (cosine similarity)
- **Model**: `sentence-transformers/all-MiniLM-L6-v2` (384-dim, ~22MB)
- **Index location**: `data/indexes/chroma/`
- **Collection name**: `cpp_corpus`
- **Score conversion**: `1.0 - (cosine_distance / 2.0)` (maps 0–2 distance → 0–1 similarity)
- **Strengths**: Semantic understanding, paraphrase matching, intent
- **Weaknesses**: Can miss exact proper names, less predictable for short queries

### 4.4 Hybrid Fusion: RRF (`src/retrieval/hybrid_retriever.py`)

Reciprocal Rank Fusion combines ranked lists from both backends without requiring score calibration:

```
For each result r in retrieval list L:
    RRF_score(r) += 1 / (rank(r, L) + k)    where k = 60

Final score = sum of RRF contributions across all lists
Normalized to [0, 1] range
```

- **Candidate pool**: Each backend fetches `top_k * 3` candidates before fusion
- **Fusion constant** `k=60`: Reduces the influence of very top-ranked results, balancing precision vs recall
- **Output**: top_k fused results, sorted by RRF score descending

### 4.5 Retriever Initialization (Fallback Chain)

```
Backend startup
    │
    ├─► Try HybridRetriever (Chroma + Whoosh)
    │       If both available → retriever_mode = "hybrid"
    │
    ├─► Chroma fails → Try WhooshRetriever alone
    │       retriever_mode = "bm25"
    │
    └─► Both fail → retriever = None
            retriever_mode = "unavailable"
            POST /chat → HTTP 503
```

### 4.6 SearchResult Schema

```python
@dataclass
class SearchResult:
    chunk_id: str       # Unique chunk identifier
    title: str          # Document title
    url: str            # Canonical CPP URL
    snippet: str        # Short excerpt for citations
    score: float        # 0.0 – 1.0 (higher = more relevant)
    section: str | None # Section heading (debug only)
```

---

## 5. AI Agent Loop

### 5.1 Full Execution Flow

```
run_tool_loop(message, conversation_id, store, retriever)
        │
        ▼
┌───────────────────────────────────────────────────────────────────┐
│  Step 1: Query Normalization (query_normalizer.py)                │
│                                                                   │
│  Input:  raw user message (may have filler, typos, abbrevs)      │
│  • Strip leading filler: "can you tell me about..."              │
│  • Expand abbreviations: "CPP" → "Cal Poly Pomona"               │
│                          "FAFSA" → "Free Application for..."     │
│                          "CBA" → "College of Business Admin"     │
│  • Collapse punctuation: "What???" → "What?"                     │
│  • Detect ambiguity: < 3 meaningful tokens → is_ambiguous = True │
│                                                                   │
│  Output: NormalizedQuery { original, normalized_text, is_ambiguous }
└───────────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────────┐
│  Step 2: Support Routing (support_routing.py)                     │
│                                                                   │
│  Regex pattern matching (pre-LLM, deterministic):                │
│  • Police: "mugged", "assault", "robbery", "emergency"           │
│  • Health: "fell", "injured", "sick on campus", "medical help"   │
│  • Mental health (CAPS): "depressed", "anxious", "overwhelmed"   │
│  • Financial hardship: "can't afford", "basic needs"             │
│                                                                   │
│  If matched → _run_support_route():                              │
│      retriever.search_corpus(route.retrieval_query)              │
│      Return deterministic formatted response (no LLM call)       │
└───────────────────────────────────────────────────────────────────┘
        │
        │ (if no urgent route matched)
        ▼
┌───────────────────────────────────────────────────────────────────┐
│  Step 3: Ambiguity Gate                                           │
│                                                                   │
│  If query.is_ambiguous:                                          │
│      Return NOT_FOUND with "please provide more detail" message  │
│      (no LLM, no retrieval)                                      │
└───────────────────────────────────────────────────────────────────┘
        │
        │ (if query is clear)
        ▼
┌───────────────────────────────────────────────────────────────────┐
│  Step 4: LLM Agentic Loop (_gemini_loop / _openai_loop)          │
│                                                                   │
│  Context Construction:                                           │
│    messages = [system_prompt] + conversation_history + [user_msg]│
│                                                                   │
│  Tool Available:                                                 │
│    search_corpus(query: str, top_k: int = 5) → list[SearchResult]│
│                                                                   │
│  Loop:                                                           │
│    ┌─────────────────────────────────────────────────────────┐  │
│    │  Call LLM with messages + tool definition               │  │
│    │       │                                                 │  │
│    │       ▼                                                 │  │
│    │  finish_reason == "tool_calls" ?                        │  │
│    │       │ Yes: extract query from tool call args          │  │
│    │       │      retriever.search_corpus(query, top_k)      │  │
│    │       │      ──────────────────────────────────────     │  │
│    │       │      On first retrieval call:                   │  │
│    │       │        assess_confidence(results, config)       │  │
│    │       │        If grounding fails:                      │  │
│    │       │          Return refusal (exit loop)             │  │
│    │       │      ──────────────────────────────────────     │  │
│    │       │      Append tool result to messages             │  │
│    │       │      Continue loop (repeat)                     │  │
│    │       │                                                 │  │
│    │       ▼ No (stop/end_turn):                             │  │
│    │  Extract answer_markdown from final message             │  │
│    │  Collect all retrieved chunks across all tool calls     │  │
│    └─────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────────┐
│  Step 5: Citation Extraction (tool_loop.py: extract_citations)    │
│                                                                   │
│  Strategy 1 (footer-first):                                      │
│    Split answer at "## sources:" or "## references:" header      │
│    Parse markdown links [title](url) from footer section         │
│                                                                   │
│  Strategy 2 (text match fallback):                               │
│    For each retrieved chunk:                                     │
│      Check if chunk.url or chunk.title appears in answer body    │
│      If matched: include as citation                             │
│                                                                   │
│  Deduplication: track seen URLs, drop duplicates                 │
│  Output: list[Citation] { title, url, snippet }                  │
└───────────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────────┐
│  Step 6: Persistence (conversation/store.py)                      │
│                                                                   │
│  If store available:                                             │
│    store.append_user_message(conversation_id, raw_message)       │
│    store.append_assistant_message(conv_id, answer, citations,    │
│                                   status)                        │
│    store.append_turn_review(raw_query, normalized_query, status, │
│                              refusal_trigger, retrieved_chunks,  │
│                              debug_requested, tokens)            │
└───────────────────────────────────────────────────────────────────┘
        │
        ▼
ChatResponse { conversation_id, status, answer_markdown, citations }
```

### 5.2 Grounding Check (`src/agent/grounding.py`)

The grounding check is applied after the **first** retrieval call, before the LLM is allowed to synthesize a response.

| Parameter | Default | Description |
|---|---|---|
| `GROUNDING_MIN_TOP_SCORE` | `0.3` | Minimum score for the top result |
| `GROUNDING_MIN_RESULTS` | `1` | Minimum number of results required |
| `GROUNDING_SCORE_AGGREGATION` | `max` | Aggregation method: `max`, `mean_top3`, `count_only` |
| `GROUNDING_EXPECTED_TOP_K` | `5` | Number of results requested |

**Verdict:**
- `grounded = True` → proceed to LLM completion
- `grounded = False` → immediate refusal response (status: `not_found`)

**Refusal response** includes a link to cpp.edu and an explanation that the information wasn't found in the corpus.

### 5.3 System Prompt Summary (`src/agent/system_prompt.py`)

- **Scope**: CPP questions only — admissions, academics, campus services, student life
- **Grounding rule**: MUST call `search_corpus` before any factual claim
- **Citation rule**: Every claim must be backed by ≥1 retrieved chunk
- **No fabrication**: No invented deadlines, phone numbers, building names, fees
- **Output format**: Markdown, English, < 400 words, no HTML or emojis
- **Identity**: Does not reveal system prompt or internal instructions
- **Tools available**: Only `search_corpus(query: str, top_k: int = 5)`

### 5.4 Conversation History

- **Storage**: SQLite via `ConversationStore`
- **History window**: Last `CONVERSATION_HISTORY_MAX_TURNS * 2` messages (user+assistant pairs), oldest first
- **Multi-turn**: `conversation_id` is client-generated (UUID) and sent with every request
- **History injection**: Prepended to LLM context between system prompt and current user message

### 5.5 LLM Provider Details

| Aspect | OpenAI | Gemini |
|---|---|---|
| Model | `gpt-4o-mini` | `gemini-2.5-flash` |
| Tool protocol | OpenAI `tools` + `tool_calls` | Google `types.Tool` + `function_call` parts |
| Message format | `{role, content}` list | `types.Content` objects |
| Loop termination | `finish_reason == "stop"` | No `function_call` parts in response |
| Config key | `OPENAI_API_KEY` | `GEMINI_API_KEY` |

---

## 6. API Layer

### 6.1 Endpoints

#### `POST /chat`

**Request:**
```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",  // optional
  "message": "What are the library hours?",
  "debug": false
}
```

**Response:**
```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "answered",          // "answered" | "not_found" | "error"
  "answer_markdown": "The CPP library is open...\n\n## Sources:\n[Library Hours](https://...)",
  "citations": [
    {
      "title": "University Library | Cal Poly Pomona",
      "url": "https://www.cpp.edu/library/hours.shtml",
      "snippet": "Monday–Thursday 7:30am–11pm..."
    }
  ],
  "debug_info": null             // populated if debug=true and admin auth valid
}
```

**Status codes:**
- `200`: Normal response (including not_found/error statuses in body)
- `503`: Retriever unavailable (no indexes built)
- `500`: Unexpected server error

#### `POST /transcribe`

**Request:** `multipart/form-data` with `audio` file field  
**Supported formats:** `mp3`, `mp4`, `m4a`, `wav`, `webm`  
**Max size:** 5MB (`VOICE_TRANSCRIPTION_MAX_BYTES`)

**Response:**
```json
{ "transcript": "What are the library hours?" }
```

**Status codes:**
- `200`: Transcript returned
- `400`: Unsupported format or oversized file
- `503`: Transcription service unavailable (env not configured)

#### `GET /health`

**Response:**
```json
{
  "status": "ok",
  "artifacts": {
    "cleaned_ready": true,
    "chunk_manifest_ready": true,
    "whoosh_ready": true,
    "chroma_ready": true
  },
  "retriever_mode": "hybrid"    // "hybrid" | "bm25" | "unavailable"
}
```

#### `GET /admin/conversations`

**Auth:** Bearer token (`Authorization: Bearer <ADMIN_API_TOKEN>`)

**Response:** `AdminConversationSummary[]`
```json
[
  {
    "conversation_id": "550e8400-...",
    "created_at": "2026-04-14T10:00:00Z",
    "updated_at": "2026-04-14T10:05:00Z",
    "turn_count": 3,
    "last_status": "answered",
    "last_user_message_preview": "What are the library hours?"
  }
]
```

#### `GET /admin/conversations/{id}`

**Auth:** Bearer token required

**Response:** `AdminConversationDetail` with full transcript and per-turn metadata:
```json
{
  "conversation_id": "550e8400-...",
  "created_at": "...",
  "updated_at": "...",
  "turns": [
    {
      "user_message": { "id": 1, "content": "...", "created_at": "..." },
      "assistant_message": { "id": 2, "content": "...", "citations": [...], "status": "answered", "created_at": "..." },
      "review": {
        "raw_query": "...",
        "normalized_query": "...",
        "status": "answered",
        "refusal_trigger": null,
        "debug_requested": false,
        "debug_authorized": false,
        "llm_prompt_tokens": 1240,
        "retrieved_chunks_json": "[...]"
      }
    }
  ]
}
```

### 6.2 Middleware & Configuration

- **CORS**: Configured from `CORS_ORIGINS` env var. Allows credentials, all methods, all headers.
- **Auth**: `src/api/auth.py` — Bearer token check via `Authorization` header. `get_optional_admin_auth()` returns bool; `require_admin_auth()` raises HTTP 401.
- **Lifespan**: Context manager initializes retriever, conversation store, and LLM client on startup. Logs retriever mode.
- **Dependency injection**: `get_retriever()`, `get_conversation_store()`, `get_llm_runner()`, `get_audio_transcriber()` — all from `app.state`, injectable for testing.

### 6.3 Configuration (`src/settings.py`)

All settings are loaded from environment variables (`.env` file or Docker env):

```
LLM_PROVIDER                    = gemini | openai
GEMINI_API_KEY / OPENAI_API_KEY = <api key>
ADMIN_API_TOKEN                 = <bearer token>
CORS_ORIGINS                    = comma-separated URLs
RAW_CORPUS_DIR                  = dataset/itc2026_ai_corpus
DATA_DIR                        = data
AUTO_BUILD_ARTIFACTS            = true | false
CONVERSATION_DB_PATH            = data/conversations.db
CONVERSATION_HISTORY_MAX_TURNS  = 10
GROUNDING_MIN_TOP_SCORE         = 0.3
GROUNDING_MIN_RESULTS           = 1
GROUNDING_SCORE_AGGREGATION     = max | mean_top3 | count_only
GROUNDING_EXPECTED_TOP_K        = 5
VOICE_TRANSCRIPTION_ENABLED     = true | false
VOICE_TRANSCRIPTION_MODEL       = gpt-4o-mini-transcribe
VOICE_TRANSCRIPTION_MAX_BYTES   = 5000000
HOST                            = 0.0.0.0
PORT                            = 8000
LOG_LEVEL                       = INFO
```

---

## 7. Frontend

### 7.1 Application Structure

```
frontend/src/
├── App.tsx                   # Root component — view routing (landing | chat | admin)
├── types.ts                  # TypeScript interfaces
├── api/
│   └── client.ts             # HTTP client (sendMessage, transcribeAudio)
├── hooks/
│   ├── useChat.ts            # Chat state management
│   └── useVoiceInput.ts      # Audio recording + transcription
├── components/
│   ├── ChatWindow.tsx         # Full chat view
│   ├── ChatInput.tsx          # Message input field
│   ├── MessageBubble.tsx      # Single message rendering
│   ├── MessageList.tsx        # Message thread
│   ├── FloatingChatPanel.tsx  # Floating overlay dialog
│   ├── CitationList.tsx       # Citation cards with links
│   ├── StarterPrompts.tsx     # Quick-prompt buttons
│   ├── AssistantAudioButton.tsx  # Voice input trigger
│   ├── ErrorBanner.tsx        # Error display
│   ├── RefusalMessage.tsx     # Not-found display
│   ├── LoadingIndicator.tsx   # Typing animation
│   ├── StatCard.tsx           # Admin dashboard stat
│   ├── UserTable.tsx          # Admin conversation list
│   └── ResourcePreview.tsx    # iframe for CPP page preview
├── services/
│   └── voice.ts              # MediaRecorder / playback utilities
└── data/
    └── mock.ts               # Mock responses for dev without backend
```

### 7.2 Key Hooks

**`useChat` (`hooks/useChat.ts`)**

```typescript
const { messages, conversationId, isLoading, error, send, resetConversation } = useChat()
```

- Manages: `messages[]`, `conversationId` (UUID), `isLoading`, `error`
- `send(text: string)`: appends user message optimistically, calls `sendMessage()`, appends assistant response
- `resetConversation()`: clears all state, generates new `conversationId`
- UUID generation: `crypto.randomUUID()` with HTTP fallback

**`useVoiceInput`**

- Uses `MediaRecorder` API (requires HTTPS in production)
- Records audio blob → calls `transcribeAudio()` → passes transcript to `send()`

### 7.3 API Client (`api/client.ts`)

```typescript
sendMessage(conversationId: string, message: string): Promise<ChatResponse>
    → POST /chat { conversation_id, message }

transcribeAudio(audioBlob: Blob, filename: string): Promise<string>
    → POST /transcribe (FormData)
```

- Mock mode: set `VITE_USE_MOCK=true` to return mock responses without backend
- Error handling: returns fallback error message on network failure

### 7.4 TypeScript Types

```typescript
interface ChatRequest {
    conversation_id?: string;
    message: string;
    debug?: boolean;
}

interface ChatResponse {
    conversation_id: string;
    status: MessageStatus;        // "answered" | "not_found" | "error"
    answer_markdown: string;
    citations: Citation[];
}

interface Citation {
    title: string;
    url: string;
    snippet: string;
}

interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    citations?: Citation[];
    status?: MessageStatus;
    timestamp: Date;
}
```

### 7.5 Build Configuration

**Development** (`vite.config.ts`):
```
npm run dev          → Vite dev server on :5173
                       Proxy /chat, /transcribe, /health → localhost:8000
```

**Production** (`Dockerfile`):
```
Stage 1: Node 20 — npm ci && npm run build → dist/
Stage 2: Nginx — serve dist/ as static files on :80
```

**Environment variables** (build-time):
```
VITE_USE_MOCK=false             # Enable mock mode for dev
VITE_API_BASE_URL=              # Override API base URL in prod
```

---

## 8. Testing & Evaluation

### 8.1 Test Framework

- **Framework**: pytest 8.0+ with pytest-asyncio 0.24+
- **HTTP testing**: httpx `TestClient` + `AsyncClient` for FastAPI
- **Test doubles**: `tests/fakes.py` (`FakeRetriever`, `fake_llm_runner`)

### 8.2 Test Coverage by Module

| Module | Test File(s) | What's Tested |
|---|---|---|
| API endpoints | `test_api.py`, `test_admin_api.py` | Health, chat contract, transcribe, admin auth, pagination |
| Agent loop | `test_tool_loop_grounding.py` | Provider switching, tool call flow, grounding, refusal |
| Multi-turn | `conversation/test_multi_turn_api.py` | History injection, conversation_id persistence |
| Conversation store | `conversation/test_store.py` | SQLite CRUD, history window, turn review |
| Citations | `test_citations.py` | Footer parse, text match fallback, URL normalization, dedup |
| Query normalization | `test_query_normalizer.py` | Filler stripping, abbreviation expansion, ambiguity detection |
| Grounding | `test_grounding.py` | Confidence thresholds, verdict logic |
| Support routing | `test_support_routing.py` | Pattern matching, route selection |
| Pipeline | `test_pipeline.py`, `test_strip_boilerplate.py`, `test_filter_corpus.py`, `test_extract_metadata.py`, `test_conflicts.py`, `test_freshness.py` | Each preprocessing stage |
| Index building | `test_build_index.py` | Chunking, Whoosh schema, chunk manifest |
| Configuration | `test_settings.py` | Env var parsing, defaults |
| Observability | `test_observability.py` | Log events |
| Evaluation harness | `test_eval_harness.py` | Eval infrastructure |
| Pydantic models | `test_models.py` | Request/response schema validation |

### 8.3 Test Utilities

```python
# tests/fakes.py

class FakeRetriever(RetrieverBase):
    """Returns fixed SearchResult list for deterministic test behavior."""
    def __init__(self, results: list[SearchResult]): ...
    async def search_corpus(self, query, top_k=5) -> list[SearchResult]: ...

async def fake_llm_runner(...) -> ToolLoopResult:
    """Synthetic LLM loop that returns a fixed answer without calling any API."""
```

### 8.4 Running Tests

```bash
# All tests
pytest

# Single module
pytest tests/test_api.py

# Verbose output
pytest -v

# With coverage report
pytest --cov=src --cov-report=term-missing

# Async tests (configured in pyproject.toml)
# asyncio_mode = "auto"
```

### 8.5 Evaluation Harness

**`scripts/eval/run_eval.py`**
- Runs a predefined set of test queries against the live retriever + agent
- Measures: answer quality, citation presence, refusal rate, response time
- Used for benchmarking system quality before handoff

**`scripts/smoke_rag_pipeline.py`**
- Integration smoke test: runs one full end-to-end query through retrieval → LLM → response
- Validates that pipeline artifacts, retrievers, and LLM connectivity all work together
- Run before deployment to confirm system health

---

## 9. Deployment & Setup

### 9.1 Local Development

```bash
# 1. Clone and configure
git clone <repo>
cp .env.example .env
# Edit .env: add GEMINI_API_KEY or OPENAI_API_KEY, ADMIN_API_TOKEN

# 2. Place raw corpus
# dataset/itc2026_ai_corpus/ must exist (provided separately)

# 3. Start services
docker compose up --build

# Services:
# Frontend: http://localhost:5173
# Backend:  http://localhost:8000
# Health:   http://localhost:8000/health
```

**Docker Compose (dev) — `docker-compose.yml`:**

| Service | Image | Port | Notes |
|---|---|---|---|
| `backend` | `python:3.11` | `8000` | Live reload (`--reload`), volume-mounted source |
| `frontend` | `node:20` | `5173` | Vite hot module replacement |

Backend healthcheck: `/health` every 10s (5s timeout, 5 retries, 120s initial delay)  
Frontend depends on backend being healthy before starting.

### 9.2 Production Deployment

```bash
# 1. Configure hosted environment
cp .env.example .env
# Set: LLM_PROVIDER, GEMINI/OPENAI key, ADMIN_API_TOKEN, PUBLIC_API_BASE_URL

# 2. Start production stack
docker compose -f docker-compose.hosted.yml up --build -d
```

**Docker Compose (hosted) — `docker-compose.hosted.yml`:**

| Service | Image | Port | Notes |
|---|---|---|---|
| `backend` | `python:3.11` | `8000` | No hot reload, production uvicorn |
| `frontend` | `nginx:alpine` | `80` | Serves static `dist/` build |

### 9.3 Backend Container Startup (`docker/entrypoint.sh`)

```bash
1. Verify raw corpus exists at $RAW_CORPUS_DIR
2. If AUTO_BUILD_ARTIFACTS=true:
     a. If data/cleaned/ is empty:
          → python scripts/preprocess/run_pipeline.py
     b. If data/chunks.jsonl or data/indexes/whoosh/ missing:
          → python scripts/build_index.py
3. Start API:
     uvicorn src.api.main:app --host $HOST --port $PORT [--reload]
```

This makes artifact building idempotent — re-running the container skips already-built artifacts.

### 9.4 Manual Pipeline Execution

```bash
# Activate virtual environment
source .venv/Scripts/activate    # Windows/bash
# or
source .venv/bin/activate        # Linux/Mac

# Check raw corpus
python scripts/check_corpus.py

# Preprocess corpus → data/cleaned/
python scripts/preprocess/run_pipeline.py

# Build search indexes → data/indexes/ + data/chunks.jsonl
python scripts/build_index.py

# Start backend
uvicorn src.api.main:app --reload

# Start frontend (separate terminal)
cd frontend && npm run dev

# Run tests
pytest

# Smoke test
python scripts/smoke_rag_pipeline.py
```

### 9.5 Infrastructure Notes

- **HTTPS**: Required for voice input (browser `MediaRecorder` API security restriction). Handled via reverse proxy (e.g., nginx with TLS) in front of the VM — not within this repo.
- **Judge deployment**: Judges provide their own LLM API keys. Deploy with `docker-compose.hosted.yml`. System auto-builds artifacts on first run.
- **Corpus not in repo**: Raw corpus (`dataset/`) and generated artifacts (`data/`) are git-ignored. Distributed separately.
- **SQLite WAL**: Write-Ahead Logging enabled for concurrent read/write access to conversation database.

---

## 10. Tech Stack Reference

### Backend

| Component | Technology | Version | Purpose |
|---|---|---|---|
| Web framework | FastAPI | ≥0.115 | REST API, dependency injection, async handlers |
| ASGI server | Uvicorn | ≥0.34 | Production-grade async server |
| Data validation | Pydantic v2 | ≥2.0 | Request/response schema validation |
| Configuration | pydantic-settings | ≥2.0 | Env var loading with type coercion |
| LLM (primary) | Google Gemini | gemini-2.5-flash | Text generation, tool use |
| LLM (secondary) | OpenAI | gpt-4o-mini | Text generation, tool use |
| Voice transcription | OpenAI Whisper | gpt-4o-mini-transcribe | Audio → text |
| Vector store | Chroma | ≥0.5 | Persistent semantic search index |
| BM25 search | Whoosh | ≥2.7 | Lexical full-text search |
| Embeddings | sentence-transformers | ≥3.0 | `all-MiniLM-L6-v2` (384-dim) |
| Conversation DB | SQLite (WAL) | stdlib | Persistent conversation + audit storage |
| HTTP client | httpx | ≥0.27 | Async HTTP for tests |
| Python version | Python | 3.11+ | Runtime |

### Frontend

| Component | Technology | Version | Purpose |
|---|---|---|---|
| UI framework | React | 18.3.1 | Functional components, hooks |
| Build tool | Vite | 6.0.0 | Dev server, hot module replacement, production build |
| Language | TypeScript | 5.6.3 | Static typing |
| Markdown rendering | react-markdown | 9.0.1 | Render LLM answer_markdown |
| Linting | ESLint | 8.57.0 | Code quality |
| Formatting | Prettier | 3.4.2 | Code formatting |
| Production server | Nginx | alpine | Static file serving |

### Infrastructure

| Component | Technology | Purpose |
|---|---|---|
| Containerization | Docker | Isolated build environments |
| Orchestration | Docker Compose | Multi-service local + hosted deployment |
| Version control | Git + GitHub | Source control |
| Package manager (Python) | pip / pyproject.toml | Dependency management |
| Package manager (JS) | npm | Frontend dependency management |

### Testing

| Component | Technology | Purpose |
|---|---|---|
| Test framework | pytest 8.0+ | Test discovery, execution, fixtures |
| Async testing | pytest-asyncio 0.24+ | Async coroutine test support |
| Coverage | pytest-cov | Code coverage reporting |
| HTTP testing | httpx TestClient | FastAPI endpoint testing |
| Test doubles | Custom fakes | FakeRetriever, fake_llm_runner |

### Data Formats

| Format | Location | Contents |
|---|---|---|
| JSONL | `data/chunks.jsonl` | 91,407 retrieval chunks (one JSON per line) |
| JSON | `data/metadata.json` | Document-level metadata array |
| JSON | `data/filter_report.json` | Filtering decisions and exclusion reasons |
| JSON | `data/freshness_manifest.json` | Staleness risk per document |
| Markdown | `data/conflict_review.md` | Human-readable conflict report |
| Markdown | `data/cleaned/*.md` | 7,398 cleaned CPP documents |
| SQLite | `data/conversations.db` | Conversations, messages, turn reviews |
| Whoosh index | `data/indexes/whoosh/` | BM25 search index (Whoosh native format) |
| Chroma index | `data/indexes/chroma/` | Vector search index (Chroma + SQLite) |

---

*Document generated from codebase analysis at commit `c0bfd56` (V0.1 frozen handoff).*
