"""Tests for persisted Chroma collection detection."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.retrieval.chroma_index import (
    CHROMA_COLLECTION,
    ChromaCollectionMissingError,
    chroma_collection_exists,
    get_chroma_collection,
)

chromadb = pytest.importorskip("chromadb")


def test_chroma_collection_exists_is_false_for_empty_index(tmp_path: Path) -> None:
    assert chroma_collection_exists(tmp_path / "chroma") is False


def test_get_chroma_collection_raises_clear_error_for_missing_collection(
    tmp_path: Path,
) -> None:
    chroma_dir = tmp_path / "chroma"

    with pytest.raises(ChromaCollectionMissingError) as exc_info:
        get_chroma_collection(chroma_dir)

    assert CHROMA_COLLECTION in str(exc_info.value)
    assert str(chroma_dir) in str(exc_info.value)


def test_chroma_collection_exists_is_true_when_collection_present(
    tmp_path: Path,
) -> None:
    chroma_dir = tmp_path / "chroma"
    client = chromadb.PersistentClient(path=str(chroma_dir))
    client.create_collection(CHROMA_COLLECTION)

    assert chroma_collection_exists(chroma_dir) is True
