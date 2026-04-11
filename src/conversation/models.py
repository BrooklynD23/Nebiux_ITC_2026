"""Frozen data types for conversation memory."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

MessageRole = Literal["user", "assistant"]


@dataclass(frozen=True)
class Message:
    """A single persisted conversation turn."""

    role: MessageRole
    content: str
    created_at: datetime
    citations: list[dict] | None = None
    status: str | None = None
