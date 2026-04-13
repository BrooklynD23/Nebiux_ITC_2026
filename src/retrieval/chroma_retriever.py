"""Semantic retrieval backend using the persisted Chroma vector index."""

from __future__ import annotations

import logging

import chromadb
from sentence_transformers import SentenceTransformer

from src.models import SearchResult
from src.retrieval.interface import RetrieverBase
from src.settings import get_settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHROMA_COLLECTION = "cpp_corpus"


class ChromaRetriever(RetrieverBase):
    """Search the CPP corpus using semantic similarity via Chroma."""

    def __init__(self) -> None:
        settings = get_settings()
        chroma_dir = settings.index_dir / "chroma"

        logger.info("Loading embedding model '%s'...", EMBEDDING_MODEL)
        self._model = SentenceTransformer(EMBEDDING_MODEL)

        client = chromadb.PersistentClient(path=str(chroma_dir))
        self._collection = client.get_collection(CHROMA_COLLECTION)
        logger.info("ChromaRetriever ready (%d chunks indexed)", self._collection.count())

    async def search_corpus(self, query: str, top_k: int = 5) -> list[SearchResult]:
        embedding = self._model.encode(query).tolist()

        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            include=["metadatas", "distances"],
        )

        ids = results["ids"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]  # cosine distance: 0 = identical, 2 = opposite

        output: list[SearchResult] = []
        for chunk_id, meta, distance in zip(ids, metadatas, distances):
            # Convert cosine distance to a 0–1 similarity score
            score = round(1.0 - (distance / 2.0), 4)
            output.append(
                SearchResult(
                    chunk_id=chunk_id,
                    title=meta["title"],
                    url=meta["url"],
                    snippet=meta["snippet"],
                    score=max(score, 0.0),
                )
            )

        return output
