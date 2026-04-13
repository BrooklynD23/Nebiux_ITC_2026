"""Integration tests for tool-loop grounding/refusal behavior."""

from __future__ import annotations

import pytest

from src.agent.tool_loop import run_tool_loop
from src.models import SearchResult
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


@pytest.mark.asyncio
async def test_tool_loop_weak_retrieval_returns_refusal() -> None:
    response = await run_tool_loop(
        message="What is the FAFSA deadline at CPP?",
        retriever=_EmptyRetriever(),
    )

    assert response.status.value == "not_found"
    assert response.citations == []
    assert "couldn't find enough reliable information" in response.answer_markdown
    assert (
        "free application for federal student aid deadline at cal poly pomona"
        in response.answer_markdown.lower()
    )
