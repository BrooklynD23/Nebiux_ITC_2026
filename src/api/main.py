"""FastAPI application entry-point.

Run with::

    uvicorn src.api.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router

app = FastAPI(
    title="CPP Campus Knowledge Agent",
    description=(
        "Ask natural-language questions about Cal Poly Pomona and get "
        "grounded, cited answers from the official corpus."
    ),
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# CORS — allow frontend dev servers on localhost
# ---------------------------------------------------------------------------
_ALLOWED_ORIGINS: list[str] = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe — returns 200 if the service is up."""
    return {"status": "ok"}
