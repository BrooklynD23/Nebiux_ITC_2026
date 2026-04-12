"""Chat route handler for POST /chat."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from src.agent.tool_loop import run_tool_loop
from src.conversation import ConversationStore
from src.models import ChatRequest, ChatResponse
from src.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()


def get_conversation_store(request: Request) -> ConversationStore | None:
    """Return the app-scoped conversation store, if configured.

    Returns ``None`` when the store has not been attached to ``app.state``
    (for example in legacy tests that bypass the FastAPI lifespan).
    """
    return getattr(request.app.state, "conversation_store", None)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    store: ConversationStore | None = Depends(get_conversation_store),
) -> ChatResponse:
    """Handle a user chat message and return a grounded answer."""
    try:
        response = await run_tool_loop(
            message=request.message,
            conversation_id=(
                str(request.conversation_id)
                if request.conversation_id is not None
                else None
            ),
            store=store,
            max_turns=get_settings().conversation_history_max_turns,
        )
        return response
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error in chat handler")
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred. Please try again later.",
        ) from None
