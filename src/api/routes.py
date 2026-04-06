"""Chat route handler for POST /chat."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from src.agent.tool_loop import run_tool_loop
from src.models import ChatRequest, ChatResponse, ChatStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Handle a user chat message and return a grounded answer.

    Delegates to the agent tool loop which (in Sprint 2+) will call the
    LLM with the ``search_corpus`` tool.  For Sprint 0-1 the tool loop
    returns realistic mock responses.
    """
    try:
        response = await run_tool_loop(
            message=request.message,
            conversation_id=(
                str(request.conversation_id)
                if request.conversation_id is not None
                else None
            ),
        )
        return response
    except Exception:
        logger.exception("Unexpected error in chat handler")
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred. Please try again later.",
        ) from None
