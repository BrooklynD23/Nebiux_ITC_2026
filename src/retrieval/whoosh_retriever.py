"""BM25 retrieval backend using the persisted Whoosh index."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from whoosh import index
from whoosh.qparser import MultifieldParser, OrGroup

from src.models import SearchResult
from src.retrieval.interface import RetrieverBase
from src.settings import get_settings

logger = logging.getLogger(__name__)


class WhooshRetriever(RetrieverBase):
    """Search the CPP corpus using the prebuilt Whoosh BM25 index."""

    def __init__(self) -> None:
        settings = get_settings()
        self._chunks = _load_chunks(settings.chunk_manifest_path)
        self._ix = index.open_dir(str(settings.whoosh_dir))
        self._parser = MultifieldParser(
            ["content", "title", "heading"],
            schema=self._ix.schema,
            group=OrGroup,
        )
        logger.info("WhooshRetriever ready (%d chunks loaded)", len(self._chunks))

    async def search_corpus(self, query: str, top_k: int = 5) -> list[SearchResult]:
        with self._ix.searcher() as searcher:
            parsed = self._parser.parse(query)
            hits = searcher.search(parsed, limit=top_k)

            if not hits:
                return []

            top_score = hits[0].score or 1.0
            results: list[SearchResult] = []

            for hit in hits:
                chunk = self._chunks.get(hit["chunk_id"])
                if chunk is None:
                    continue
                results.append(
                    SearchResult(
                        chunk_id=hit["chunk_id"],
                        title=hit["title"],
                        url=hit["url"],
                        snippet=chunk["snippet"],
                        score=round(min(hit.score / top_score, 1.0), 4),
                    )
                )

        return results


def _load_chunks(path: Path) -> dict[str, dict]:
    """Load chunks.jsonl into a dict keyed by chunk_id."""
    if not path.is_file():
        raise FileNotFoundError(
            f"Chunk manifest not found: {path}. Run scripts/build_index.py first."
        )
    chunks: dict[str, dict] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunk = json.loads(line)
                chunks[chunk["chunk_id"]] = chunk
    logger.debug("Loaded %d chunks from %s", len(chunks), path)
    return chunks
