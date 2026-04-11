# Issue Audit: Setup Gemini API Call (main branch)

Date: 2026-04-11
Branch audited: `origin/main`

## Summary

The Gemini API **skeleton is partially established** on main:

- ✅ provider selection + API key contract exists (`LLM_PROVIDER`, `GEMINI_API_KEY`)
- ✅ shared LLM client factory exists (`src/config.py:get_llm_client`)
- ✅ environment docs/examples already include Gemini variables
- ❌ Gemini client is **not wired into the `/chat` execution path**
- ❌ no provider-backed tool loop yet for corpus search / RAG grounding

## What already exists on `main`

1. **Central provider config**
   - `src/settings.py` defines:
     - `LLM_PROVIDER` (default `gemini`)
     - `GEMINI_API_KEY`
     - `OPENAI_API_KEY`

2. **LLM client factory**
   - `src/config.py` defines:
     - `LLMProvider` enum (`gemini`, `openai`)
     - `get_llm_client()` which constructs `google.genai.Client` when provider is Gemini
     - key validation with clear missing-env errors

3. **Team-facing env/docs contract**
   - `.env.example` includes Gemini/OpenAI variables.
   - `README.md` has an **LLM Provider Note** stating Gemini as the target and that the live provider-backed loop is not enabled yet.

## Current gap blocking team use in corpus/RAG files

- `src/agent/tool_loop.py` is still a keyword-based mock response stub and does not call:
  - `get_llm_client()`
  - `search_corpus` retrieval backend
  - provider APIs (Gemini/OpenAI)
- `src/retrieval/` currently contains only the retrieval interface + stub backend, so the real RAG chain is not integrated with an LLM call path yet.

## Practical conclusion

Other teams can already import `src.config.get_llm_client()` as a stable contract, but they cannot yet rely on an end-to-end Gemini-powered corpus/RAG chat flow on `main` because the runtime tool loop is still scaffold-level.
