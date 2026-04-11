"""Unit tests for ConversationStore."""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone

import pytest

from src.conversation import ConversationStore, Message


def test_get_or_create_mints_new_id_when_none(store: ConversationStore) -> None:
    cid = store.get_or_create(None)
    # Round-trip UUID string
    parsed = uuid.UUID(cid)
    assert str(parsed) == cid
    # History is empty for a brand new conversation
    assert store.get_history(cid, max_turns=5) == []


def test_get_or_create_honors_supplied_id(store: ConversationStore) -> None:
    cid = str(uuid.uuid4())
    first = store.get_or_create(cid)
    second = store.get_or_create(cid)
    assert first == cid
    assert second == cid
    # Idempotent: calling twice does not raise, and history remains empty
    assert store.get_history(cid, max_turns=5) == []


def test_append_user_message_persists_fields(store: ConversationStore) -> None:
    cid = store.get_or_create(None)
    msg = store.append_user_message(cid, "hello world")
    assert isinstance(msg, Message)
    assert msg.role == "user"
    assert msg.content == "hello world"
    assert msg.created_at.tzinfo is not None
    assert msg.created_at.tzinfo.utcoffset(msg.created_at) == timezone.utc.utcoffset(
        datetime.now(timezone.utc)
    )
    history = store.get_history(cid, max_turns=5)
    assert [m.role for m in history] == ["user"]
    assert history[0].content == "hello world"


def test_append_assistant_message_persists_citations_and_status(
    store: ConversationStore,
) -> None:
    cid = store.get_or_create(None)
    citations = [
        {"title": "t", "url": "https://x", "snippet": "s"},
    ]
    store.append_assistant_message(
        cid, "answer", citations=citations, status="answered"
    )
    history = store.get_history(cid, max_turns=5)
    assert len(history) == 1
    assistant = history[0]
    assert assistant.role == "assistant"
    assert assistant.content == "answer"
    assert assistant.status == "answered"
    assert assistant.citations == citations


def test_get_history_returns_chronological_order(
    store: ConversationStore,
) -> None:
    cid = store.get_or_create(None)
    store.append_user_message(cid, "u1")
    store.append_assistant_message(cid, "a1", [], "answered")
    store.append_user_message(cid, "u2")
    store.append_assistant_message(cid, "a2", [], "answered")
    history = store.get_history(cid, max_turns=10)
    assert [m.content for m in history] == ["u1", "a1", "u2", "a2"]


def test_get_history_trims_to_last_n_turns(store: ConversationStore) -> None:
    cid = store.get_or_create(None)
    for i in range(15):
        store.append_user_message(cid, f"u{i}")
        store.append_assistant_message(cid, f"a{i}", [], "answered")
    history = store.get_history(cid, max_turns=5)
    assert len(history) == 10
    # Expect newest 5 pairs (u10..u14 / a10..a14) in chronological order
    expected = []
    for i in range(10, 15):
        expected.extend([f"u{i}", f"a{i}"])
    assert [m.content for m in history] == expected


def test_get_history_unknown_conversation_returns_empty_list(
    store: ConversationStore,
) -> None:
    assert store.get_history("no-such-id", max_turns=10) == []


def test_get_history_empty_for_brand_new_conversation(
    store: ConversationStore,
) -> None:
    cid = store.get_or_create(None)
    assert store.get_history(cid, max_turns=10) == []


def test_concurrent_writes_are_serialized(store: ConversationStore) -> None:
    cid = store.get_or_create(None)

    def worker(prefix: str) -> None:
        for i in range(20):
            store.append_user_message(cid, f"{prefix}-{i}")

    t1 = threading.Thread(target=worker, args=("A",))
    t2 = threading.Thread(target=worker, args=("B",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    history = store.get_history(cid, max_turns=100)
    assert len(history) == 40
    # All writes landed with expected payloads
    contents = {m.content for m in history}
    expected = {f"{p}-{i}" for p in ("A", "B") for i in range(20)}
    assert contents == expected
