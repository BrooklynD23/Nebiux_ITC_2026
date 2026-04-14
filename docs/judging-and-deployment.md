# Judging and Deployment Guide

This is the judge-facing runbook for the hosted demo.

## What To Expect

- The project is a web app, not a browser extension.
- The supported hosted target is a single Google Cloud VM instance running Docker Compose.
- `docker-compose.hosted.yml` exposes the frontend on port `80` and the backend on port `8000`.
- If you need HTTPS, terminate TLS outside the repo with a reverse proxy or load balancer in front of the VM. The repository does not manage certificates.
- The repo does not ship an API key.
- Planned provider:
  - primary: Gemini 2.5 Flash
  - fallback: OpenAI gpt-4o-mini

## Hosted VM Runbook

### 1. Prepare the VM

Clone the repo and create the environment file:

```bash
git clone <repo-url>
cd Nebiux_ITC_2026
cp .env.example .env
```

Install the raw CPP corpus under `dataset/itc2026_ai_corpus/`.

Reference: [dataset/README.md](../dataset/README.md)

### 2. Set the public-host values

Set these before building:

- `CORS_ORIGINS=<public frontend origin>`
- `PUBLIC_API_BASE_URL=<public backend origin>`

Examples:

- direct VM exposure: `CORS_ORIGINS=http://<vm-host-or-domain>`
- direct VM exposure: `PUBLIC_API_BASE_URL=http://<vm-host-or-domain>:8000`
- external TLS termination: use the `https://` frontend and backend URLs that the proxy or load balancer presents to judges

### 3. Start the stack

```bash
docker compose -f docker-compose.hosted.yml up -d --build
```

### 4. Verify the app

Open:

- frontend: `http://<vm-host-or-domain>/`
- backend health: `http://<vm-host-or-domain>:8000/health`

If a reverse proxy or load balancer terminates TLS, use the public `https://` URL that front door exposes instead.

## What The Backend Produces

On first boot the backend generates:

- `data/cleaned/`
- `data/metadata.json`
- `data/filter_report.json`
- `data/freshness_manifest.json`
- `data/conflict_review.md`
- `data/chunks.jsonl`
- `data/indexes/whoosh/`
- `data/indexes/chroma/`
- `data/conversations.db`

If the semantic retriever cannot initialize, the app falls back to BM25-only and still serves `/chat`.

## Voice Notes

- `POST /chat` remains text-only.
- `POST /transcribe` supports the browser recording fallback.
- On `localhost`, browsers allow microphone APIs for development.
- On a public host, microphone capture requires HTTPS in front of the VM.

## API Key Expectations

- No API key is committed to the repo.
- Judges are not expected to receive a team API key.
- If judges want to test live model responses locally, they should provide their own `GEMINI_API_KEY` or `OPENAI_API_KEY` in `.env`.

## Submission Checklist

Before final competition submission, confirm:

1. The frontend loads from a browser without local setup.
2. The hosted deployment uses the Google Cloud VM runbook above.
3. The app is served over HTTPS if the demo needs microphone support.
4. The VM can restart and rebuild artifacts from the repo plus the mounted corpus.
5. The README and this guide still match the deployed host shape.
