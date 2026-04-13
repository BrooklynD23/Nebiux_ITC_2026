"""Shared fixtures for conversation memory tests."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from src.conversation import ConversationStore


@pytest.fixture
def store(tmp_path: Path) -> Iterator[ConversationStore]:
    """Fresh SQLite-backed store on a per-test temp file."""
    s = ConversationStore(tmp_path / "test.db")
    try:
        yield s
    finally:
        s.close()
