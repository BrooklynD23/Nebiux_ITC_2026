# Judging and Deployment Guide

This document is the judge-facing setup and deployment guide for the repository.

## What Judges Need To Know

- The application is a **web app**, not a browser extension.
- The repo is runnable locally from a fresh clone.
- The team does **not** include an API key in the repo.
- Planned provider:
  - primary: Gemini 2.5 Flash
  - fallback: OpenAI gpt-4o-mini

## Local Clone-and-Run

### 1. Clone and prepare the corpus

```bash
git clone <repo-url>
cd Nebiux_ITC_2026
cp .env.example .env
```

Install the raw CPP corpus under `dataset/itc2026_ai_corpus/`.

Reference: [dataset/README.md](../dataset/README.md)

### 2. Recommended local run

```bash
docker compose up --build
```

Open:

- frontend: `http://localhost:5173`
- backend health: `http://localhost:8000/health`

### 3. What the backend generates automatically

On first boot the backend will generate:

- `data/cleaned/`
- `data/metadata.json`
- `data/filter_report.json`
- `data/chunks.jsonl`
- `data/indexes/whoosh/`
- `data/indexes/chroma/`
- `data/conversations.db`

If the semantic retriever cannot initialize, the app falls back to BM25-only and still serves `/chat`.

## Hosted Deployment

### Recommended judge-facing architecture

- single VM
- Docker Compose
- static frontend on port `80`
- FastAPI backend on port `8000`

Recommended host: **Oracle Cloud**

Fallback host: **AWS EC2**

### Deploy commands

On the VM:

```bash
git clone <repo-url>
cd Nebiux_ITC_2026
cp .env.example .env
```

Set the following before building:

- `CORS_ORIGINS=http://<server-ip-or-domain>`
- `PUBLIC_API_BASE_URL=http://<server-ip-or-domain>:8000`

Then run:

```bash
docker compose -f docker-compose.hosted.yml up -d --build
```

Judge-facing frontend:

- `http://<server-ip-or-domain>/`

Backend health:

- `http://<server-ip-or-domain>:8000/health`

The health response includes artifact readiness and the active retriever mode.

## Why Vercel Is Not The Primary Recommendation

Vercel is acceptable for a static frontend, but not as the primary full-stack host for this repo because:

- the backend depends on persisted local retrieval artifacts
- the backend is not designed as a serverless function package
- local index files are a better fit for a VM than an ephemeral/serverless filesystem model

## API Key Expectations

- No API key is committed to the repo.
- Judges are not expected to receive a team API key.
- When provider-backed answers are enabled, judges who want to test that path locally should supply their own `GEMINI_API_KEY` or `OPENAI_API_KEY` in `.env`.

## Submission Checklist

Before final competition submission, fill in the live demo URL in the submission materials and confirm:

1. the frontend loads from a browser without local setup
2. the VM can restart and rebuild artifacts from the repo + corpus mount
3. the README and this file still match the deployed host shape
