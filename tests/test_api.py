"""Tests for the FastAPI chat and health handlers."""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from src.api.main import health
from src.api.routes import chat
from src.models import ChatRequest
from tests.fakes import FakeRetriever, fake_llm_runner


class TestHealthEndpoint:
    """Verify the liveness probe."""

    @pytest.mark.asyncio
    async def test_health_returns_ok(self) -> None:
        data = await health()
        assert data["status"] == "ok"


class TestChatEndpoint:
    """Verify the chat handler returns valid contract shapes."""

    @pytest.mark.asyncio
    async def test_chat_returns_valid_shape(self) -> None:
        response = await chat(
            ChatRequest(message="What are the admission deadlines?"),
            store=None,
            retriever=FakeRetriever(),
            llm_runner=fake_llm_runner,
        )
        data = response.model_dump()

        assert "conversation_id" in data
        assert "status" in data
        assert "answer_markdown" in data
        assert "citations" in data
        assert data["status"] in ("answered", "not_found", "error")

    @pytest.mark.asyncio
    async def test_chat_preserves_conversation_id(self) -> None:
        cid = uuid.uuid4()
        response = await chat(
            ChatRequest(message="Tell me about CPP", conversation_id=cid),
            store=None,
            retriever=FakeRetriever(),
            llm_runner=fake_llm_runner,
        )
        assert response.conversation_id == str(cid)

    @pytest.mark.asyncio
    async def test_chat_generates_conversation_id(self) -> None:
        response = await chat(
            ChatRequest(message="Hello"),
            store=None,
            retriever=FakeRetriever(),
            llm_runner=fake_llm_runner,
        )
        assert len(response.conversation_id) > 0

    @pytest.mark.asyncio
    async def test_chat_citations_shape(self) -> None:
        response = await chat(
            ChatRequest(message="What are the admission deadlines?"),
            store=None,
            retriever=FakeRetriever(),
            llm_runner=fake_llm_runner,
        )
        data = response.model_dump()
        for citation in data["citations"]:
            assert "title" in citation
            assert "url" in citation
            assert "snippet" in citation

    @pytest.mark.asyncio
    async def test_chat_ambiguous_query_returns_clarification(self) -> None:
        response = await chat(
            ChatRequest(message="hi"),
            store=None,
            retriever=FakeRetriever(),
            llm_runner=fake_llm_runner,
        )
        data = response.model_dump()

        assert data["status"] == "not_found"
        assert data["citations"] == []
        assert "could you give me more detail" in data["answer_markdown"]

    @pytest.mark.asyncio
    async def test_chat_normalized_query_hits_financial_aid_response(self) -> None:
        response = await chat(
            ChatRequest(message="  FAFSA DUE WHEN?? "),
            store=None,
            retriever=FakeRetriever(),
            llm_runner=fake_llm_runner,
        )
        data = response.model_dump()

        assert data["status"] == "answered"
        assert data["citations"][0]["title"] == "Financial Aid and Scholarships"

    def test_chat_rejects_empty_message(self) -> None:
        with pytest.raises(ValidationError):
            ChatRequest(message="")

    def test_chat_rejects_missing_message(self) -> None:
        with pytest.raises(ValidationError):
            ChatRequest.model_validate({})

    def test_chat_rejects_invalid_conversation_id(self) -> None:
        with pytest.raises(ValidationError):
            ChatRequest(message="Hello", conversation_id="not-a-uuid")

    @pytest.mark.asyncio
    async def test_chat_debug_requires_admin_authorization(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await chat(
                ChatRequest(message="Tell me about CPP", debug=True),
                store=None,
                retriever=FakeRetriever(),
                llm_runner=fake_llm_runner,
                admin_debug_authorized=False,
            )

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_chat_debug_returns_debug_info_when_authorized(self) -> None:
        response = await chat(
            ChatRequest(message="Tell me about CPP", debug=True),
            store=None,
            retriever=FakeRetriever(),
            llm_runner=fake_llm_runner,
            admin_debug_authorized=True,
        )

        assert response.debug_info is not None
        assert response.debug_info.raw_query == "Tell me about CPP"
        assert response.debug_info.normalized_query == "tell me about Cal Poly Pomona"
        assert response.debug_info.retrieved_chunks[0].chunk_id == "about-001"
