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
Write `src/agent/prompts.py`. Grounds the LLM to CPP campus info, tells it how to call `search_corpus`, sets citation format.

## Step 6 — Real Tool Loop
Replace the stub in `src/agent/tool_loop.py`. Calls LLM → detects `search_corpus` tool call → runs hybrid retriever → feeds chunks back → returns final answer with citations.
