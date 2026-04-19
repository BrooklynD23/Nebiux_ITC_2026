"""Unit tests for ConversationStore."""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone

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


def test_append_turn_review_persists_and_lists_conversation_summary(
    store: ConversationStore,
) -> None:
    cid = store.get_or_create(None)
    user = store.append_user_message(cid, "What are parking rules?")
    assistant = store.append_assistant_message(cid, "Parking answer", [], "answered")

    review = store.append_turn_review(
        conversation_id=cid,
        user_message_id=user.id,
        assistant_message_id=assistant.id,
        raw_query="What are parking rules?",
        normalized_query="what are parking rules",
        status="answered",
        refusal_trigger=None,
        debug_requested=True,
        debug_authorized=True,
        llm_prompt_tokens=42,
        retrieved_chunks=[
            {
                "chunk_id": "parking-001",
                "title": "Parking and Transportation",
                "section": None,
                "url": "https://www.cpp.edu/parking/permits/index.shtml",
                "score": 0.92,
                "snippet": "Parking permits are required.",
            }
        ],
    )

    assert review.conversation_id == cid
    assert review.user_message_id == user.id
    assert review.assistant_message_id == assistant.id
    assert review.debug_requested is True
    assert review.llm_prompt_tokens == 42

    summaries = store.list_conversation_summaries(limit=10, offset=0)
    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.conversation_id == cid
    assert summary.turn_count == 1
    assert summary.last_status == "answered"
    assert "parking" in summary.last_user_message_preview.lower()
    assert summary.last_query_latency_ms is not None
    assert summary.last_query_latency_ms >= 0
    assert summary.is_dangerous_query is False


def test_list_conversation_summaries_flags_dangerous_latest_query(
    store: ConversationStore,
) -> None:
    cid = store.get_or_create(None)
    user = store.append_user_message(
        cid,
        "I am in emotional distress and need help right now.",
    )
    assistant = store.append_assistant_message(
        cid,
        "Please contact support resources.",
        [],
        "answered",
    )
    store.append_turn_review(
        conversation_id=cid,
        user_message_id=user.id,
        assistant_message_id=assistant.id,
        raw_query=user.content,
        normalized_query="i am in emotional distress and need help right now",
        status="answered",
        refusal_trigger=None,
        debug_requested=False,
        debug_authorized=False,
        llm_prompt_tokens=5,
        retrieved_chunks=[],
    )

    summaries = store.list_conversation_summaries(limit=10, offset=0)

    assert len(summaries) == 1
    assert summaries[0].is_dangerous_query is True


def test_get_conversation_detail_returns_turn_review_metadata(
    store: ConversationStore,
) -> None:
    cid = store.get_or_create(None)
    user = store.append_user_message(cid, "Tell me about FAFSA")
    assistant = store.append_assistant_message(
        cid,
        "Financial aid answer",
        [],
        "answered",
    )
    store.append_turn_review(
        conversation_id=cid,
        user_message_id=user.id,
        assistant_message_id=assistant.id,
        raw_query="Tell me about FAFSA",
        normalized_query="tell me about fafsa",
        status="answered",
        refusal_trigger=None,
        debug_requested=False,
        debug_authorized=False,
        llm_prompt_tokens=11,
        retrieved_chunks=[
            {
                "chunk_id": "aid-001",
                "title": "Financial Aid and Scholarships",
                "section": None,
                "url": "https://www.cpp.edu/financial-aid/index.shtml",
                "score": 0.95,
                "snippet": "CPP offers grants and scholarships.",
            }
        ],
    )

    detail = store.get_conversation_detail(cid)

    assert detail is not None
    assert detail.conversation_id == cid
    assert len(detail.turns) == 1
    turn = detail.turns[0]
    assert turn.user_message.content == "Tell me about FAFSA"
    assert turn.assistant_message.content == "Financial aid answer"
    assert turn.review.normalized_query == "tell me about fafsa"
    assert turn.review.retrieved_chunks[0]["chunk_id"] == "aid-001"
