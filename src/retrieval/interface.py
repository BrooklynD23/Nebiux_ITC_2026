"""Abstract retrieval interface for the search_corpus tool.

All retrieval backends (BM25, semantic, hybrid) implement this protocol
so the agent tool loop can call ``search_corpus`` without knowing the
underlying engine.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.models import SearchResult


class RetrieverBase(ABC):
    """Abstract base for corpus retrieval backends."""

    @abstractmethod
    async def search_corpus(
        self, query: str, top_k: int = 5
    ) -> list[SearchResult]:
        """Search the CPP corpus and return ranked results.

        Parameters
        ----------
        query:
            Natural-language search query.
        top_k:
            Maximum number of results to return.

        Returns
        -------
        list[SearchResult]
            Ranked search results with relevance scores.
        """
        ...  # pragma: no cover
