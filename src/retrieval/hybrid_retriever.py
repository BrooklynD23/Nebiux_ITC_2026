"""Hybrid retrieval backend combining BM25 and semantic search via RRF."""

from __future__ import annotations

import logging

from src.models import SearchResult
from src.retrieval.chroma_retriever import ChromaRetriever
from src.retrieval.interface import RetrieverBase
from src.retrieval.whoosh_retriever import WhooshRetriever

logger = logging.getLogger(__name__)

# RRF constant — 60 is the standard default from the original paper
_RRF_K = 60


class HybridRetriever(RetrieverBase):
    """Combine BM25 and semantic results using Reciprocal Rank Fusion."""

    def __init__(self) -> None:
        self._bm25 = WhooshRetriever()
        self._semantic = ChromaRetriever()
        logger.info("HybridRetriever ready")

    async def search_corpus(self, query: str, top_k: int = 5) -> list[SearchResult]:
        # Fetch more candidates from each retriever before fusing
        candidate_k = top_k * 3

        bm25_results = await self._bm25.search_corpus(query, top_k=candidate_k)
        semantic_results = await self._semantic.search_corpus(query, top_k=candidate_k)

        fused = _reciprocal_rank_fusion(bm25_results, semantic_results)
        return fused[:top_k]


def _reciprocal_rank_fusion(
    *result_lists: list[SearchResult],
) -> list[SearchResult]:
    """Merge ranked result lists using Reciprocal Rank Fusion.

    Each result gets a score of 1 / (rank + k) from each list it appears in.
    Final scores are summed and results re-ranked.
    """
    rrf_scores: dict[str, float] = {}
    # Keep one SearchResult per chunk_id to reconstruct results after fusion
    seen: dict[str, SearchResult] = {}

    for results in result_lists:
        for rank, result in enumerate(results):
            rrf_scores[result.chunk_id] = (
                rrf_scores.get(result.chunk_id, 0.0) + 1.0 / (rank + _RRF_K)
            )
            seen.setdefault(result.chunk_id, result)

    # Normalize RRF scores to 0–1 relative to the highest score
    if not rrf_scores:
        return []

    max_score = max(rrf_scores.values())
    ranked = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)

    return [
        seen[cid].model_copy(update={"score": round(rrf_scores[cid] / max_score, 4)})
        for cid in ranked
    ]
