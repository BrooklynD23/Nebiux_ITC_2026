# V0.1 Adversarial Review

Last updated: 2026-04-05

## Purpose

This document is the active risk register for V0.1. Its job is not to restate every earlier criticism, but to keep the team from drifting back into high-risk scope.

## Current Verdict

V0.1 is feasible for three contributors only if the project stays contract-first and demo-first. The main risks are no longer architectural ambition alone. The biggest risk is uncontrolled parallel work that creates schema churn and integration thrash.

## Top Risks

### 1. Preprocessing rules are too brittle

Risk:
- fixed-line stripping will remove real content on some pages and leave junk on others

Why it matters:
- retrieval quality fails before BM25 or embeddings ever have a chance

Countermeasure:
- use structure-based stripping
- detect duplicate nav blocks, login gates, redirect pages, and low-value hubs
- preserve tables and headings as first-class acceptance criteria

### 2. Parallel contributors can accidentally create interface churn

Risk:
- frontend, backend, and eval each invent their own response format

Why it matters:
- integration work consumes the sprint instead of delivering features

Countermeasure:
- Sprint 0 freezes `POST /chat`, `search_corpus`, and citation schemas
- mock fixtures and eval parsers must use the same contract

### 3. Evaluation arrives too late

Risk:
- retrieval and refusal behavior get tuned by instinct until the end

Why it matters:
- the team can think the system works until live demo questions expose misses

Countermeasure:
- build the first 12-15 golden cases in Sprint 0
- expand the set only after core E2E is working

### 4. UI scope grows faster than trust value

Risk:
- extra routes, analytics, or ornamental UI consume time that should go to core trust signals

Why it matters:
- judges care more about grounded answers and clear citations than dashboard breadth

Countermeasure:
- one chat route only for V0.1
- put visible citations, refusal states, and supporting snippets ahead of additional pages

### 5. Stretch features leak into the core plan

Risk:
- rerankers, analytics, and extra tools become unplanned dependencies

Why it matters:
- the finish line moves and the core demo slips

Countermeasure:
- exactly one showcase lane, started only after Sprint 2 exit criteria are met

## Go / No-Go Rules

Go:
- preprocessing outputs are stable
- chat schema is stable
- end-to-end grounded answers work locally
- setup steps are reproducible

No-Go:
- schema churn continues past Sprint 0
- frontend depends on undefined fields
- analytics or extra tools start before core E2E is stable
- retrieval quality is being tuned without eval cases

## Scope Guardrails

Keep:
- web app
- single-model, single-tool architecture
- hybrid retrieval as a technique, not as a justification for extra complexity
- citation-first trust model

Defer:
- analytics dashboard
- reranker unless recall targets are missed
- any route beyond the core chat page

Reject for V0.1:
- extension-style delivery
- council-of-agents
- profile memory and recommendation engines
- broad UX extras not tied to judge trust
