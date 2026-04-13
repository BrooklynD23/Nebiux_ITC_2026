# RAG Implementation Plan

## Step 1 — BM25 Retriever
Implement `src/retrieval/whoosh_retriever.py`. Loads `data/chunks.jsonl` and queries the persisted Whoosh index.

## Step 2 — Semantic Index Build
Update `scripts/build_index.py` to embed chunks using `sentence-transformers` and persist them into Chroma at `data/indexes/chroma/`.

## Step 3 — Semantic Retriever
Implement `src/retrieval/chroma_retriever.py`. Embeds the query and does a vector similarity search against Chroma.

## Step 4 — Hybrid Retriever
Implement `src/retrieval/hybrid_retriever.py`. Runs both retrievers, fuses scores with Reciprocal Rank Fusion, returns unified ranked results.

## Step 5 — System Prompt
Use `src/agent/system_prompt.py` as the canonical grounding prompt. Keep `src/agent/prompts.py` only as a compatibility alias.

## Step 6 — Real Tool Loop
`src/agent/tool_loop.py` now owns the live flow:

- normalize query
- short-circuit ambiguous requests
- call the provider tool loop
- execute `search_corpus` against the app-scoped retriever
- gate weak retrieval with `src.agent.grounding`
- return grounded markdown plus citations
- persist multi-turn conversation state through `ConversationStore`
