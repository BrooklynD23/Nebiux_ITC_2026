"""Tests for Pydantic model validation."""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from src.models import (
    ChatRequest,
    ChatResponse,
    ChatStatus,
    Citation,
    SearchResult,
)


class TestChatRequest:
    """Validate ChatRequest construction and constraints."""

    def test_message_required(self) -> None:
        with pytest.raises(ValidationError):
            ChatRequest()  # type: ignore[call-arg]

    def test_message_cannot_be_empty(self) -> None:
        with pytest.raises(ValidationError):
            ChatRequest(message="")

    def test_message_max_length(self) -> None:
        with pytest.raises(ValidationError):
            ChatRequest(message="x" * 2001)

    def test_conversation_id_generated_when_omitted(self) -> None:
        req = ChatRequest(message="Hello")
        assert req.conversation_id is not None
        assert isinstance(req.conversation_id, uuid.UUID)

    def test_conversation_id_preserved_when_provided(self) -> None:
        cid = str(uuid.uuid4())
        req = ChatRequest(message="Hello", conversation_id=cid)
        assert str(req.conversation_id) == cid

    def test_conversation_id_must_be_uuid(self) -> None:
        with pytest.raises(ValidationError):
            ChatRequest(message="Hello", conversation_id="my-custom-id")

    def test_valid_request(self) -> None:
        req = ChatRequest(message="What are the admission deadlines?")
        assert req.message == "What are the admission deadlines?"


class TestChatResponse:
    """Validate ChatResponse shape matches the contract."""

    def test_full_response(self) -> None:
        resp = ChatResponse(
            conversation_id="abc-123",
            status=ChatStatus.ANSWERED,
            answer_markdown="Some answer",
            citations=[
                Citation(
                    title="Page",
                    url="https://example.com",
                    snippet="excerpt",
                )
            ],
        )
        assert resp.status == ChatStatus.ANSWERED
        assert len(resp.citations) == 1

    def test_empty_citations_for_error(self) -> None:
        resp = ChatResponse(
            conversation_id="abc-123",
            status=ChatStatus.ERROR,
            answer_markdown="Something went wrong.",
        )
        assert resp.citations == []

    def test_invalid_status_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ChatResponse(
                conversation_id="abc",
                status="invalid_status",  # type: ignore[arg-type]
                answer_markdown="test",
            )


class TestSearchResult:
    """Validate SearchResult model."""

    def test_valid_result(self) -> None:
        result = SearchResult(
            chunk_id="chunk-001",
            title="Test Page",
            url="https://www.cpp.edu/test",
            snippet="A test snippet.",
            score=0.85,
        )
        assert result.score == 0.85

    def test_score_out_of_range(self) -> None:
        with pytest.raises(ValidationError):
            SearchResult(
                chunk_id="chunk-001",
                title="Test",
                url="https://example.com",
                snippet="text",
                score=1.5,
            )

    def test_negative_score_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SearchResult(
                chunk_id="chunk-001",
                title="Test",
                url="https://example.com",
                snippet="text",
                score=-0.1,
            )
