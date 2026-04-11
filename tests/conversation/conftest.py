"""Shared fixtures for conversation memory tests."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from src.conversation import ConversationStore


@pytest.fixture
def store(tmp_path: Path) -> Iterator[ConversationStore]:
    """Fresh SQLite-backed store on a per-test temp file."""
    s = ConversationStore(tmp_path / "test.db")
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def client_with_store(
    store: ConversationStore,
) -> Iterator[AsyncClient]:
    """AsyncClient bound to the FastAPI app with ``store`` pre-attached.

    Bypasses the real lifespan so each test starts with an isolated
    SQLite file without interfering with ``tests/test_api.py`` which
    intentionally runs without a store.
    """
    from src.api.main import app

    prior = getattr(app.state, "conversation_store", None)
    app.state.conversation_store = store
    try:
        yield AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        )
    finally:
        if prior is None:
            if hasattr(app.state, "conversation_store"):
                del app.state.conversation_store
        else:
            app.state.conversation_store = prior
