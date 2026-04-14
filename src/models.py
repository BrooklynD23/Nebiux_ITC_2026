"""Pydantic models for API request/response contracts and internal data."""

from __future__ import annotations

import uuid
from datetime import datetime
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
    debug: bool = Field(
        default=False,
        description="Request privileged debug information for this chat turn.",
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


class RetrievedChunkDebug(BaseModel):
    """Retrieved chunk metadata for debug and admin review surfaces."""

    chunk_id: str = Field(..., description="Unique identifier for the chunk.")
    title: str = Field(..., description="Title of the source document.")
    section: str | None = Field(
        default=None,
        description="Optional section heading within the source document.",
    )
    url: str = Field(..., description="Canonical URL to the source page.")
    snippet: str = Field(..., description="Relevant text excerpt.")
    score: float = Field(
        ..., ge=0.0, le=1.0, description="Relevance score between 0 and 1."
    )


class ChatDebugInfo(BaseModel):
    """Privileged diagnostic details for an authorized chat request."""

    raw_query: str = Field(..., description="Original user input.")
    normalized_query: str = Field(..., description="Normalized retrieval query.")
    retrieved_chunks: list[RetrievedChunkDebug] = Field(
        default_factory=list,
        description="Retrieved chunks considered during the turn.",
    )
    refusal_trigger: str | None = Field(
        default=None,
        description="Reason code when the request is refused or not grounded.",
    )
    llm_prompt_tokens: int | None = Field(
        default=None,
        ge=0,
        description="Provider-reported prompt tokens used for the turn.",
    )


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
    debug_info: ChatDebugInfo | None = Field(
        default=None,
        description="Privileged debug details for authorized callers.",
    )


class TranscriptionResponse(BaseModel):
    """Response payload for POST /transcribe."""

    transcript: str = Field(..., description="Trimmed transcript text.")


class SearchResult(BaseModel):
    """A single item returned by the search_corpus tool."""

    chunk_id: str = Field(..., description="Unique identifier for the chunk.")
    title: str = Field(..., description="Title of the source document.")
    section: str | None = Field(
        default=None,
        description="Optional section heading for the matched chunk.",
    )
    url: str = Field(..., description="Canonical URL to the source page.")
    snippet: str = Field(..., description="Relevant text excerpt.")
    score: float = Field(
        ..., ge=0.0, le=1.0, description="Relevance score between 0 and 1."
    )
