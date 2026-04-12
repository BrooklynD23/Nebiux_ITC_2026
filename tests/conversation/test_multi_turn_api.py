"""Integration tests for multi-turn /chat wiring against ConversationStore."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient

from src.agent import tool_loop as tool_loop_module
from src.conversation import ConversationStore, Message


@pytest.fixture
def spy(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Replace the stub generator with a spy capturing its arguments."""
    captured: list[dict[str, Any]] = []
    real = tool_loop_module._generate_stub_response

    def _spy(message: str, cid: str, history: list[Message]):
        captured.append(
            {
                "message": message,
                "conversation_id": cid,
                "history": list(history),
            }
        )
        return real(message, cid, history)

    monkeypatch.setattr(tool_loop_module, "_generate_stub_response", _spy)
    return captured


@pytest.mark.asyncio
async def test_first_turn_creates_conversation_and_persists_user_message(
    client_with_store: AsyncClient,
    store: ConversationStore,
) -> None:
    async with client_with_store as client:
        response = await client.post(
            "/chat",
            json={"message": "Tell me about parking"},
        )
    assert response.status_code == 200
    cid = response.json()["conversation_id"]
    history = store.get_history(cid, max_turns=10)
    assert [m.role for m in history] == ["user", "assistant"]
    assert history[0].content == "Tell me about parking"


@pytest.mark.asyncio
async def test_second_turn_sees_prior_history(
    client_with_store: AsyncClient,
    spy: list[dict[str, Any]],
) -> None:
    cid = str(uuid.uuid4())
    async with client_with_store as client:
        await client.post(
            "/chat",
            json={"conversation_id": cid, "message": "What are parking rules?"},
        )
        await client.post(
            "/chat",
            json={"conversation_id": cid, "message": "And on weekends?"},
        )
    assert len(spy) == 2
    first_history = spy[0]["history"]
    second_history = spy[1]["history"]
    assert first_history == []
    assert [m.role for m in second_history] == ["user", "assistant"]
    assert second_history[0].content == "What are parking rules?"


@pytest.mark.asyncio
async def test_unknown_client_supplied_conversation_id_is_accepted(
    client_with_store: AsyncClient,
    store: ConversationStore,
) -> None:
    cid = str(uuid.uuid4())
    async with client_with_store as client:
        response = await client.post(
            "/chat",
            json={"conversation_id": cid, "message": "Hello"},
        )
    assert response.status_code == 200
    assert response.json()["conversation_id"] == cid
    assert len(store.get_history(cid, max_turns=10)) == 2


@pytest.mark.asyncio
async def test_history_trims_at_configured_limit(
    client_with_store: AsyncClient,
    spy: list[dict[str, Any]],
) -> None:
    cid = str(uuid.uuid4())
    async with client_with_store as client:
        for i in range(12):
            await client.post(
                "/chat",
                json={
                    "conversation_id": cid,
                    "message": f"question {i}",
                },
            )
        await client.post(
            "/chat",
            json={
                "conversation_id": cid,
                "message": "final question",
            },
        )
    final_history = spy[-1]["history"]
    # Default max_turns = 10 → up to 20 messages
    assert len(final_history) == 20
    # Newest window should include the immediately prior question
    assert final_history[-2].content == "question 11"


@pytest.mark.asyncio
async def test_user_append_failure_returns_500(
    client_with_store: AsyncClient,
    store: ConversationStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("disk full")

    monkeypatch.setattr(store, "append_user_message", _boom)
    async with client_with_store as client:
        response = await client.post(
            "/chat",
            json={"message": "hi"},
        )
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_assistant_append_failure_still_returns_answer(
    client_with_store: AsyncClient,
    store: ConversationStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("disk full")

    monkeypatch.setattr(store, "append_assistant_message", _boom)
    async with client_with_store as client:
        response = await client.post(
            "/chat",
            json={"message": "Tell me about parking"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["answer_markdown"]
