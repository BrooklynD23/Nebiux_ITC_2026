# Sprint 3 - Hardening and Showcase

Last updated: 2026-04-05

## Goal

Reduce demo risk first. Add at most one showcase feature only after the core system is stable.

## Contributor A - Retrieval Hardening

Focus:
- inspect misses from eval outputs
- tune retrieval parameters conservatively
- add reranker only if simpler fixes fail

Do not:
- redesign the retrieval stack late in V0.1

## Contributor B - Runtime and Delivery Hardening

Focus:
- latency improvements
- startup and shutdown flow
- environment setup clarity
- graceful failures when API key, model, or backend is unavailable

Do not:
- expand public API surface unless needed for the core demo

## Contributor C - Demo and Showcase Lane

Focus:
- final UI polish for trust and clarity
- demo script, screenshots, and local run instructions
- one showcase feature after the core gate passes

Recommended showcase:
- source provenance inspector showing supporting snippets and linked pages

Deferred unless everything is already green:
- analytics dashboard
- extra navigation routes
- ornamental UI work

## Exit Criteria

- README setup is reproducible from a clean clone
- demo questions are rehearsed and stable
- no unresolved core blockers remain
- if a showcase feature exists, it does not destabilize the core path
