"""Integration tests for multi-turn chat wiring against ConversationStore."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi import HTTPException

from src.api.routes import chat
from src.conversation import ConversationStore, Message
from src.models import ChatRequest
from tests.fakes import FakeRetriever, fake_llm_runner


@pytest.fixture
def spy() -> tuple[list[dict[str, Any]], object]:
    """Wrap the fake runner and capture the history passed into it."""
    captured: list[dict[str, Any]] = []

    async def _spy(message: str, history: list[Message], retriever):
        captured.append(
            {
                "message": message,
                "history": list(history),
            }
        )
        return await fake_llm_runner(message, history, retriever)

    return captured, _spy


@pytest.mark.asyncio
async def test_first_turn_creates_conversation_and_persists_user_message(
    store: ConversationStore,
) -> None:
    response = await chat(
        ChatRequest(message="Tell me about parking"),
        store=store,
        retriever=FakeRetriever(),
        llm_runner=fake_llm_runner,
    )
    cid = response.conversation_id
    history = store.get_history(cid, max_turns=10)
    assert [message.role for message in history] == ["user", "assistant"]
    assert history[0].content == "Tell me about parking"


@pytest.mark.asyncio
async def test_second_turn_sees_prior_history(
    store: ConversationStore,
    spy: tuple[list[dict[str, Any]], object],
) -> None:
    captured, runner = spy
    cid = uuid.uuid4()
    await chat(
        ChatRequest(conversation_id=cid, message="What are parking rules?"),
        store=store,
        retriever=FakeRetriever(),
        llm_runner=runner,
    )
    await chat(
        ChatRequest(conversation_id=cid, message="And on weekends?"),
        store=store,
        retriever=FakeRetriever(),
        llm_runner=runner,
    )
    assert len(captured) == 2
    first_history = captured[0]["history"]
    second_history = captured[1]["history"]
    assert first_history == []
    assert [message.role for message in second_history] == ["user", "assistant"]
    assert second_history[0].content == "What are parking rules?"


@pytest.mark.asyncio
async def test_unknown_client_supplied_conversation_id_is_accepted(
    store: ConversationStore,
) -> None:
    cid = uuid.uuid4()
    response = await chat(
        ChatRequest(conversation_id=cid, message="Hello"),
        store=store,
        retriever=FakeRetriever(),
        llm_runner=fake_llm_runner,
    )
    assert response.conversation_id == str(cid)
    assert len(store.get_history(str(cid), max_turns=10)) == 2


@pytest.mark.asyncio
async def test_history_trims_at_configured_limit(
    store: ConversationStore,
    spy: tuple[list[dict[str, Any]], object],
) -> None:
    captured, runner = spy
    cid = uuid.uuid4()
    for index in range(12):
        await chat(
            ChatRequest(conversation_id=cid, message=f"parking question {index}"),
            store=store,
            retriever=FakeRetriever(),
            llm_runner=runner,
        )
    await chat(
        ChatRequest(conversation_id=cid, message="final parking question"),
        store=store,
        retriever=FakeRetriever(),
        llm_runner=runner,
    )
    final_history = captured[-1]["history"]
    assert len(final_history) == 20
    assert final_history[-2].content == "parking question 11"


@pytest.mark.asyncio
async def test_user_append_failure_returns_500(
    store: ConversationStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("disk full")

    monkeypatch.setattr(store, "append_user_message", _boom)
    with pytest.raises(HTTPException) as exc_info:
        await chat(
            ChatRequest(message="hi"),
            store=store,
            retriever=FakeRetriever(),
            llm_runner=fake_llm_runner,
        )
    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_assistant_append_failure_still_returns_answer(
    store: ConversationStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("disk full")

    monkeypatch.setattr(store, "append_assistant_message", _boom)
    response = await chat(
        ChatRequest(message="Tell me about parking"),
        store=store,
        retriever=FakeRetriever(),
        llm_runner=fake_llm_runner,
    )
    assert response.status.value == "answered"
    assert response.answer_markdown
