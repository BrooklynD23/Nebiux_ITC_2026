"""Tests for admin auth and read-only conversation review routes."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from src.api.admin import get_admin_conversation, list_admin_conversations
from src.api.auth import get_optional_admin_auth, require_admin_auth
from src.conversation import ConversationStore


@pytest.fixture
def store(tmp_path) -> ConversationStore:
    s = ConversationStore(tmp_path / "admin-test.db")
    try:
        yield s
    finally:
        s.close()


def test_get_optional_admin_auth_returns_false_for_invalid_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.api.auth.get_settings",
        lambda: type("SettingsStub", (), {"admin_api_token": "pilot-secret"})(),
    )

    assert get_optional_admin_auth("Bearer nope") is False


def test_require_admin_auth_accepts_valid_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.api.auth.get_settings",
        lambda: type("SettingsStub", (), {"admin_api_token": "pilot-secret"})(),
    )

    assert require_admin_auth("Bearer pilot-secret") is True


def test_require_admin_auth_rejects_missing_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.api.auth.get_settings",
        lambda: type("SettingsStub", (), {"admin_api_token": "pilot-secret"})(),
    )

    with pytest.raises(HTTPException) as exc_info:
        require_admin_auth(None)

    assert exc_info.value.status_code == 401


def test_list_admin_conversations_returns_summaries(
    store: ConversationStore,
) -> None:
    cid = store.get_or_create(None)
    user = store.append_user_message(cid, "What are parking rules?")
    assistant = store.append_assistant_message(cid, "Parking answer", [], "answered")
    store.append_turn_review(
        conversation_id=cid,
        user_message_id=user.id,
        assistant_message_id=assistant.id,
        raw_query="What are parking rules?",
        normalized_query="what are parking rules",
        status="answered",
        refusal_trigger=None,
        debug_requested=False,
        debug_authorized=False,
        llm_prompt_tokens=7,
        retrieved_chunks=[],
    )

    summaries = list_admin_conversations(store=store, _admin_authorized=True)

    assert len(summaries) == 1
    assert summaries[0].conversation_id == cid


def test_get_admin_conversation_returns_detail(
    store: ConversationStore,
) -> None:
    cid = store.get_or_create(None)
    user = store.append_user_message(cid, "Tell me about FAFSA")
    assistant = store.append_assistant_message(cid, "Aid answer", [], "answered")
    store.append_turn_review(
        conversation_id=cid,
        user_message_id=user.id,
        assistant_message_id=assistant.id,
        raw_query="Tell me about FAFSA",
        normalized_query="tell me about fafsa",
        status="answered",
        refusal_trigger=None,
        debug_requested=True,
        debug_authorized=True,
        llm_prompt_tokens=19,
        retrieved_chunks=[],
    )

    detail = get_admin_conversation(cid, store=store, _admin_authorized=True)

    assert detail.conversation_id == cid
    assert detail.turns[0].review.llm_prompt_tokens == 19
