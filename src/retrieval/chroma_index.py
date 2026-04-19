"""Shared helpers for the persisted Chroma semantic index."""

from __future__ import annotations

from pathlib import Path
from typing import Any

CHROMA_COLLECTION = "cpp_corpus"


class ChromaCollectionMissingError(RuntimeError):
    """Raised when the persisted semantic index is missing its collection."""

    def __init__(
        self,
        chroma_dir: Path,
        collection_name: str = CHROMA_COLLECTION,
    ) -> None:
        super().__init__(
            f"Chroma collection '{collection_name}' not found in {chroma_dir}. "
            "Run scripts/build_index.py to build the semantic index."
        )
        self.chroma_dir = chroma_dir
        self.collection_name = collection_name


def _load_chromadb() -> tuple[Any, type[Exception]]:
    import chromadb
    from chromadb.errors import NotFoundError

    return chromadb, NotFoundError


def get_chroma_collection(
    chroma_dir: Path,
    collection_name: str = CHROMA_COLLECTION,
):
    """Return the persisted Chroma collection or raise a clear missing error."""
    chromadb, not_found_error = _load_chromadb()
    client = chromadb.PersistentClient(path=str(chroma_dir))
    try:
        return client.get_collection(collection_name)
    except not_found_error as exc:
        raise ChromaCollectionMissingError(chroma_dir, collection_name) from exc


def chroma_collection_exists(
    chroma_dir: Path,
    collection_name: str = CHROMA_COLLECTION,
) -> bool:
    """Return whether the persisted Chroma collection is available."""
    try:
        get_chroma_collection(chroma_dir, collection_name)
    except ImportError:
        return False
    except ChromaCollectionMissingError:
        return False
    except Exception:
        return False
    return True
