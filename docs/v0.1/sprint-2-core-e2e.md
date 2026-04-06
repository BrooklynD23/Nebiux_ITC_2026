# Sprint 2 - Core End-to-End

Last updated: 2026-04-05

## Goal

Integrate retrieval, backend, and frontend until the local app satisfies the core competition brief end to end.

## Contributor A - Retrieval Integration

Sequence:
- implement heading-aware chunking
- implement BM25
- measure against the thin golden set
- add semantic retrieval and hybrid fusion only if it improves recall

Acceptance criteria:
- top results are anchored to cleaned corpus content, not boilerplate
- tables and heading context survive chunking
- retrieval quality is measured, not guessed

## Contributor B - Tool Loop and Grounding

Sequence:
- wire `search_corpus` to the live retrieval layer
- implement tool loop and conversation memory
- implement refusal behavior and citation dedupe
- ensure only grounded citations are emitted

Acceptance criteria:
- follow-up questions use the same `conversation_id`
- unsupported questions return `not_found`
- citations are deduplicated and normalized

## Contributor C - Live UI Integration

Sequence:
- replace mock API with the live `/chat` call
- validate markdown rendering and source display
- verify starter prompts, reset flow, loading, and failure states
- expand eval coverage where real misses appear

Acceptance criteria:
- a user can ask a question, receive a grounded answer, inspect sources, and ask a follow-up
- the UI handles backend failures gracefully
- the app remains a single clean route

## Exit Criteria

- local setup yields a working chat app
- answers are grounded and cited
- follow-up questions work
- the thin golden set passes at an acceptable level for the core demo
