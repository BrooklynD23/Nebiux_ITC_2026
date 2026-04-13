"""Chat route handler for POST /chat."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from src.agent.tool_loop import run_tool_loop
from src.api.auth import get_optional_admin_auth
from src.conversation import ConversationStore
from src.models import ChatRequest, ChatResponse
from src.observability import log_event
from src.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()


def get_conversation_store(request: Request) -> ConversationStore | None:
    """Return the app-scoped conversation store, if configured.

    Returns ``None`` when the store has not been attached to ``app.state``
    (for example in legacy tests that bypass the FastAPI lifespan).
    """
    return getattr(request.app.state, "conversation_store", None)


def get_retriever(request: Request) -> object | None:
    """Return the app-scoped retriever, if configured."""
    return getattr(request.app.state, "retriever", None)


def get_llm_runner(request: Request) -> object | None:
    """Return an injected tool-loop runner for tests, if configured."""
    return getattr(request.app.state, "llm_runner", None)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    store: ConversationStore | None = Depends(get_conversation_store),
    retriever: object | None = Depends(get_retriever),
    llm_runner: object | None = Depends(get_llm_runner),
    admin_debug_authorized: Annotated[bool, Depends(get_optional_admin_auth)] = False,
) -> ChatResponse:
    """Handle a user chat message and return a grounded answer."""
    if request.debug and not admin_debug_authorized:
        log_event(
            logger,
            logging.WARNING,
            "chat.admin_debug_denied",
            conversation_id=(
                str(request.conversation_id)
                if request.conversation_id is not None
                else None
            ),
        )
        raise HTTPException(
            status_code=401,
            detail="Admin authorization required for debug mode.",
        )
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
            retriever=retriever,
            llm_runner=llm_runner,
            debug_requested=request.debug,
            debug_authorized=admin_debug_authorized,
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
