# Plan: Wire Gemini into Corpus Search / RAG Flow

Date: 2026-04-11
Related audit: `docs/issue-setup-gemini-api-call-audit.md`

## Goal

Use the existing provider contract (`src/config.py`) to enable a real provider-backed `/chat` flow that calls `search_corpus` and returns grounded, cited answers.

## Minimal implementation sequence

1. **Tool loop provider integration**
   - Update `src/agent/tool_loop.py` to initialize the active client with `get_llm_client()`.
   - Keep provider-agnostic behavior by using `get_provider()` branching only where SDK call shapes differ.

2. **Retrieval invocation in loop**
   - Instantiate the selected retriever backend and call `search_corpus(query, top_k)` from within the loop.
   - Feed retrieved chunks into model context before answer generation.

3. **Citation mapping**
   - Convert retrieved chunks into existing `Citation` schema (`title`, `url`, `snippet`) in `ChatResponse`.
   - Enforce `not_found` response behavior when retrieval results are empty/low-confidence.

4. **Prompt + tool contract alignment**
   - Keep `src/agent/system_prompt.py` as the grounding contract.
   - Ensure runtime behavior matches: factual claims only from retrieved corpus chunks.

5. **Tests (focused)**
   - Add unit tests for:
     - provider selection path (`gemini` default, `openai` fallback)
     - tool loop behavior with mocked Gemini client + mocked retriever
     - citation and `not_found` status mapping

6. **Operational docs**
   - Update README “LLM Provider Note” from “scaffold-level tool loop” to “provider-backed loop” once merged.
   - Keep `.env.example` unchanged unless new variables are required.

## Suggested ownership split

- Backend/agent lane: `src/agent/tool_loop.py`, `src/api/routes.py`
- Retrieval lane: concrete retriever wiring under `src/retrieval/`
- Config lane: `src/config.py`, `src/settings.py`, env/docs touch-ups

## Exit criteria

- `/chat` uses Gemini when `LLM_PROVIDER=gemini` and key is present.
- `/chat` can still switch to OpenAI via env without code changes.
- Responses include grounded citations sourced from retrieval output.
- New/updated tests pass for provider selection and tool-loop grounding behavior.
