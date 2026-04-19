"""Frozen data types for conversation memory."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

MessageRole = Literal["user", "assistant"]


@dataclass(frozen=True)
class Message:
    """A single persisted conversation turn."""

    id: int
    role: MessageRole
    content: str
    created_at: datetime
    citations: list[dict] | None = None
    status: str | None = None


@dataclass(frozen=True)
class TurnReview:
    """Stored review metadata for a completed chat turn."""

    conversation_id: str
    user_message_id: int
    assistant_message_id: int
    raw_query: str
    normalized_query: str
    status: str
    refusal_trigger: str | None
    debug_requested: bool
    debug_authorized: bool
    llm_prompt_tokens: int | None
    retrieved_chunks: list[dict]
    created_at: datetime


@dataclass(frozen=True)
class ConversationSummary:
    """List-view summary for one persisted conversation."""

    conversation_id: str
    created_at: datetime
    updated_at: datetime
    turn_count: int
    last_status: str | None
    last_user_message_preview: str | None
    last_query_latency_ms: int | None
    is_dangerous_query: bool


@dataclass(frozen=True)
class ConversationTurn:
    """One user/assistant exchange plus review metadata."""

    user_message: Message
    assistant_message: Message
    review: TurnReview


@dataclass(frozen=True)
class ConversationDetail:
    """Transcript and review metadata for one conversation."""

    conversation_id: str
    created_at: datetime
    updated_at: datetime
    turns: list[ConversationTurn]
