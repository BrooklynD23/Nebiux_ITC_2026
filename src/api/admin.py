"""Read-only admin routes for reviewing persisted conversations."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from src.api.auth import require_admin_auth
from src.api.routes import get_conversation_store
from src.conversation import ConversationStore
from src.models import AdminConversationDetail, AdminConversationSummary

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/conversations", response_model=list[AdminConversationSummary])
def list_admin_conversations(
    limit: int = 50,
    offset: int = 0,
    store: ConversationStore | None = Depends(get_conversation_store),
    _admin_authorized: Annotated[bool, Depends(require_admin_auth)] = False,
) -> list[AdminConversationSummary]:
    """Return paginated conversation summaries for the admin dashboard."""
    del _admin_authorized
    if store is None:
        raise HTTPException(
            status_code=503,
            detail="Conversation review store unavailable.",
        )
    return store.list_conversation_summaries(limit=limit, offset=offset)


@router.get(
    "/conversations/{conversation_id}",
    response_model=AdminConversationDetail,
)
def get_admin_conversation(
    conversation_id: str,
    store: ConversationStore | None = Depends(get_conversation_store),
    _admin_authorized: Annotated[bool, Depends(require_admin_auth)] = False,
) -> AdminConversationDetail:
    """Return the persisted transcript and review metadata for one conversation."""
    del _admin_authorized
    if store is None:
        raise HTTPException(
            status_code=503,
            detail="Conversation review store unavailable.",
        )

    detail = store.get_conversation_detail(conversation_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return detail
