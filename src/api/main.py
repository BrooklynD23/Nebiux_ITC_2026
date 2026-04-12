"""FastAPI application entry-point.

Run with::

    uvicorn src.api.main:app --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router
from src.conversation import ConversationStore
from src.settings import get_settings

logger = logging.getLogger(__name__)


def _dir_has_entries(path: str) -> bool:
    from pathlib import Path

    return Path(path).is_dir() and any(Path(path).iterdir())


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Open the conversation store on startup and close it on shutdown."""
    cfg = get_settings()
    store: ConversationStore | None = None
    try:
        store = ConversationStore(cfg.effective_conversation_db_path)
    except Exception:
        logger.exception(
            "Failed to initialize conversation store at %s; "
            "continuing without persistence",
            cfg.effective_conversation_db_path,
        )
    app.state.conversation_store = store
    try:
        yield
    finally:
        if store is not None:
            try:
                store.close()
            except Exception:  # pragma: no cover - defensive
                logger.exception("Failed to close conversation store cleanly")


app = FastAPI(
    title="CPP Campus Knowledge Agent",
    description=(
        "Ask natural-language questions about Cal Poly Pomona and get "
        "grounded, cited answers from the official corpus."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
app.include_router(router)


@app.get("/health")
async def health() -> dict[str, object]:
    """Liveness probe with basic artifact readiness details."""
    return {
        "status": "ok",
        "artifacts": {
            "cleaned_ready": _dir_has_entries(str(settings.cleaned_dir)),
            "chunk_manifest_ready": settings.chunk_manifest_path.is_file(),
            "whoosh_ready": _dir_has_entries(str(settings.whoosh_dir)),
        },
    }
