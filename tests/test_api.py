"""Tests for the FastAPI application endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app


@pytest.fixture
def async_client() -> AsyncClient:
    """Create an async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestHealthEndpoint:
    """Verify the liveness probe."""

    @pytest.mark.asyncio
    async def test_health_returns_ok(self, async_client: AsyncClient) -> None:
        async with async_client as client:
            response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestChatEndpoint:
    """Verify the POST /chat stub returns valid contract shapes."""

    @pytest.mark.asyncio
    async def test_chat_returns_valid_shape(
        self, async_client: AsyncClient
    ) -> None:
        async with async_client as client:
            response = await client.post(
                "/chat",
                json={"message": "What are the admission deadlines?"},
            )
        assert response.status_code == 200
        data = response.json()

        # Required fields per contract
        assert "conversation_id" in data
        assert "status" in data
        assert "answer_markdown" in data
        assert "citations" in data

        # Status must be one of the defined values
        assert data["status"] in ("answered", "not_found", "error")

    @pytest.mark.asyncio
    async def test_chat_preserves_conversation_id(
        self, async_client: AsyncClient
    ) -> None:
        cid = str(uuid.uuid4())
        async with async_client as client:
            response = await client.post(
                "/chat",
                json={"message": "Tell me about CPP", "conversation_id": cid},
            )
        assert response.status_code == 200
        assert response.json()["conversation_id"] == cid

    @pytest.mark.asyncio
    async def test_chat_generates_conversation_id(
        self, async_client: AsyncClient
    ) -> None:
        async with async_client as client:
            response = await client.post(
                "/chat",
                json={"message": "Hello"},
            )
        assert response.status_code == 200
        assert len(response.json()["conversation_id"]) > 0

    @pytest.mark.asyncio
    async def test_chat_citations_shape(
        self, async_client: AsyncClient
    ) -> None:
        async with async_client as client:
            response = await client.post(
                "/chat",
                json={"message": "What are the admission deadlines?"},
            )
        data = response.json()
        for citation in data["citations"]:
            assert "title" in citation
            assert "url" in citation
            assert "snippet" in citation

    @pytest.mark.asyncio
    async def test_chat_rejects_empty_message(
        self, async_client: AsyncClient
    ) -> None:
        async with async_client as client:
            response = await client.post(
                "/chat",
                json={"message": ""},
            )
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_chat_rejects_missing_message(
        self, async_client: AsyncClient
    ) -> None:
        async with async_client as client:
            response = await client.post(
                "/chat",
                json={},
            )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_chat_rejects_invalid_conversation_id(
        self, async_client: AsyncClient
    ) -> None:
        async with async_client as client:
            response = await client.post(
                "/chat",
                json={"message": "Hello", "conversation_id": "not-a-uuid"},
            )
        assert response.status_code == 422
