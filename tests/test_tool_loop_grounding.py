"""Integration tests for tool-loop grounding/refusal behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.agent import tool_loop as tool_loop_module
from src.agent.grounding import assess_confidence
from src.agent.tool_loop import ToolLoopExecution, run_tool_loop
from src.models import SearchResult
from src.retrieval.chroma_index import ChromaCollectionMissingError
from src.retrieval.interface import RetrieverBase


class _EmptyRetriever(RetrieverBase):
    async def search_corpus(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[SearchResult]:
        del query
        del top_k
        return []


async def _grounding_runner(
    message: str,
    history: list[object],
    retriever: RetrieverBase,
) -> ToolLoopExecution:
    del history
    results = await retriever.search_corpus(message, top_k=5)
    return ToolLoopExecution(
        retrieved=results,
        grounding_verdict=assess_confidence(results),
        grounding_query=message,
    )


@pytest.mark.asyncio
async def test_tool_loop_weak_retrieval_returns_refusal() -> None:
    response = await run_tool_loop(
        message="What is the FAFSA deadline at CPP?",
        retriever=_EmptyRetriever(),
        llm_runner=_grounding_runner,
    )

    assert response.status.value == "not_found"
    assert response.citations == []
    assert "couldn't find enough reliable information" in response.answer_markdown
    assert (
        "free application for federal student aid deadline at cal poly pomona"
        in response.answer_markdown.lower()
    )


def test_default_retriever_falls_back_to_bm25_when_chroma_collection_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from src.retrieval import hybrid_retriever, whoosh_retriever

    class BrokenHybridRetriever:
        def __init__(self) -> None:
            raise ChromaCollectionMissingError(Path("data/indexes/chroma"))

    class FakeWhooshRetriever(RetrieverBase):
        async def search_corpus(
            self,
            query: str,
            top_k: int = 5,
        ) -> list[SearchResult]:
            del query
            del top_k
            return []

    monkeypatch.setattr(hybrid_retriever, "HybridRetriever", BrokenHybridRetriever)
    monkeypatch.setattr(whoosh_retriever, "WhooshRetriever", FakeWhooshRetriever)
    monkeypatch.setattr(tool_loop_module, "_default_retriever", None)

    with caplog.at_level("INFO"):
        retriever = tool_loop_module._get_default_retriever()

    assert isinstance(retriever, FakeWhooshRetriever)
    assert "falling back to bm25-only mode" in caplog.text.lower()
