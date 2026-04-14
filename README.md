# CPP Campus Knowledge Agent

Cal Poly Pomona campus assistant built for the MISSA ITC 2026 competition.

Start here:

- [Judging and Deployment Guide](docs/judging-and-deployment.md)
- [V0.1 Frozen Status](docs/v0.1/README.md)

This repo supports a single web-app deployment:

- `frontend/`: React + Vite UI
- `src/`: FastAPI backend
- `scripts/preprocess/`: offline corpus cleanup
- `scripts/build_index.py`: offline index build
- `data/`: generated artifacts only

## Supported Runs

### Local development

Use Docker Compose for the normal contributor path:

```bash
git clone <repo-url>
cd Nebiux_ITC_2026
cp .env.example .env
docker compose up --build
```

Install the raw CPP corpus under `dataset/itc2026_ai_corpus/` first. See [dataset/README.md](dataset/README.md).

The local UI comes up on `http://localhost:5173`.

### Hosted deployment

The judge-facing hosted setup uses `docker-compose.hosted.yml` on a Google Cloud VM instance:

```bash
cp .env.example .env
# Set CORS_ORIGINS, PUBLIC_API_BASE_URL, and any provider or voice settings
docker compose -f docker-compose.hosted.yml up -d --build
```

That compose file exposes:

- frontend on port `80`
- backend on port `8000`

If you need HTTPS, terminate TLS outside the repo with a reverse proxy or load balancer in front of the VM. The repository does not bundle certificate management.

## Environment Variables

Use [`.env.example`](.env.example) as the source of truth for backend settings.

Required or commonly adjusted backend variables:

- `LLM_PROVIDER=gemini|openai`
- `GEMINI_API_KEY=...`
- `OPENAI_API_KEY=...`
- `ADMIN_API_TOKEN=...`
- `CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`
- `RAW_CORPUS_DIR=dataset/itc2026_ai_corpus`
- `DATA_DIR=data`
- `CONVERSATION_DB_PATH=data/conversations.db`
- `GROUNDING_MIN_TOP_SCORE=0.3`
- `VOICE_TRANSCRIPTION_ENABLED=true`
- `VOICE_TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe`
- `VOICE_TRANSCRIPTION_MAX_BYTES=5000000`

Frontend variables come from [`frontend/.env.example`](frontend/.env.example):

- `VITE_USE_MOCK=false`
- `VITE_API_BASE_URL=` for hosted or static builds
- `VITE_DEV_PROXY_TARGET=http://127.0.0.1:8000` for local dev

Hosted build input:

- `PUBLIC_API_BASE_URL=<public backend origin>` for `docker-compose.hosted.yml`
  For example: `http://<vm-host-or-domain>:8000`, or the HTTPS API URL exposed by your reverse proxy.

## Notes

- The repo does not include an API key.
- Judges should supply their own provider key if they want live model responses.
- Voice input works on `localhost` during development; on a hosted demo it requires HTTPS in front of the VM.
- If the semantic retriever fails to initialize, the backend falls back to BM25-only instead of stopping the app.
