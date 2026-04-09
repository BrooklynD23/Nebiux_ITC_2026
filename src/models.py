"""Pydantic models for API request/response contracts and internal data."""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class ChatStatus(str, Enum):
    """Possible response statuses for a chat interaction."""

    ANSWERED = "answered"
    NOT_FOUND = "not_found"
    ERROR = "error"


class ChatRequest(BaseModel):
    """Incoming chat message from the frontend."""

    conversation_id: Optional[uuid.UUID] = Field(
        default=None,
        description="UUID for an existing conversation; omit to start a new one.",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The user's question about Cal Poly Pomona.",
    )

    @model_validator(mode="after")
    def _assign_conversation_id(self) -> "ChatRequest":
        """Generate a conversation_id when the client does not supply one."""
        if self.conversation_id is None:
            # Return a new instance to avoid mutation
            object.__setattr__(self, "conversation_id", uuid.uuid4())
        return self


class Citation(BaseModel):
    """A single source citation attached to an answer."""

    title: str = Field(..., description="Page or document title.")
    url: str = Field(..., description="Canonical URL to the source page.")
    snippet: str = Field(..., description="Relevant excerpt from the source.")


class ChatResponse(BaseModel):
    """Response payload for POST /chat."""

    conversation_id: str = Field(..., description="UUID for this conversation.")
    status: ChatStatus = Field(..., description="Outcome of the request.")
    answer_markdown: str = Field(
        ..., description="Answer text in Markdown format."
    )
    citations: list[Citation] = Field(
        default_factory=list,
        description="Sources backing the answer (empty for not_found/error).",
    )


class SearchResult(BaseModel):
    """A single item returned by the search_corpus tool."""

    chunk_id: str = Field(..., description="Unique identifier for the chunk.")
    title: str = Field(..., description="Title of the source document.")
    url: str = Field(..., description="Canonical URL to the source page.")
    snippet: str = Field(..., description="Relevant text excerpt.")
    score: float = Field(
        ..., ge=0.0, le=1.0, description="Relevance score between 0 and 1."
    )
