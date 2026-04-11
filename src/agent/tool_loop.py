"""Stub tool loop for the LLM agent.

In Sprint 2 this will contain the real tool-calling loop that:
1. Sends user message + conversation history to the LLM
2. Detects tool_call requests for ``search_corpus``
3. Executes retrieval, feeds results back to the LLM
4. Returns the final grounded answer with citations

For Sprint 0-1, this returns a realistic mock response so the API
contract can be validated end-to-end.  The conversation memory layer
is already wired, so the Sprint 2 author only needs to replace
``_generate_stub_response``.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from fastapi import HTTPException

from src.models import ChatResponse, ChatStatus, Citation

if TYPE_CHECKING:
    from src.conversation import ConversationStore, Message

logger = logging.getLogger(__name__)


async def run_tool_loop(
    message: str,
    conversation_id: str | None = None,
    *,
    store: "ConversationStore | None" = None,
    max_turns: int = 10,
) -> ChatResponse:
    """Process a user message through the (stubbed) agent tool loop.

    When ``store`` is provided, the prior history is loaded, the new
    user turn is persisted before generation, and the assistant turn is
    persisted afterwards.  When ``store`` is ``None`` the function
    still returns a valid response (used by legacy contract tests).
    """
    if store is not None:
        cid = store.get_or_create(conversation_id)
    else:
        cid = conversation_id or str(uuid.uuid4())

    history: "list[Message]" = []
    if store is not None:
        history = store.get_history(cid, max_turns=max_turns)
        try:
            store.append_user_message(cid, message)
        except Exception:
            logger.exception(
                "Failed to persist user message for conversation %s", cid
            )
            raise HTTPException(
                status_code=500,
                detail="Conversation store unavailable",
            ) from None

    # TODO(sprint-2): replace with real LLM + search_corpus tool loop
    response = _generate_stub_response(message, cid, history)

    if store is not None:
        try:
            store.append_assistant_message(
                cid,
                response.answer_markdown,
                [c.model_dump() for c in response.citations],
                response.status.value,
            )
        except Exception:
            logger.exception(
                "Failed to persist assistant message for conversation %s",
                cid,
            )

    return response


def _generate_stub_response(
    message: str,
    conversation_id: str,
    history: "list[Message]",
) -> ChatResponse:
    """Keyword-routed stub response.

    ``history`` is threaded through so the Sprint 2 LLM author only
    needs to replace this function body.
    """
    del history  # reserved for Sprint 2 multi-turn context

    lower = message.lower()

    if any(kw in lower for kw in ("parking", "permit", "transportation")):
        return ChatResponse(
            conversation_id=conversation_id,
            status=ChatStatus.ANSWERED,
            answer_markdown=(
                "Parking permits are required on campus Monday through "
                "Thursday. You can purchase semester or daily permits online "
                "through the [CPP parking portal]"
                "(https://www.cpp.edu/parking/permits/index.shtml)."
            ),
            citations=[
                Citation(
                    title="Parking and Transportation",
                    url="https://www.cpp.edu/parking/permits/index.shtml",
                    snippet=(
                        "Parking permits are required on campus Monday through "
                        "Thursday. Students can purchase semester or daily "
                        "permits online through the CPP parking portal."
                    ),
                ),
            ],
        )

    if any(kw in lower for kw in ("admission", "apply", "freshmen", "deadline")):
        return ChatResponse(
            conversation_id=conversation_id,
            status=ChatStatus.ANSWERED,
            answer_markdown=(
                "Cal Poly Pomona accepts **fall admission** applications from "
                "**October 1 through December 15**. You must meet CSU "
                "eligibility requirements, including completion of the A-G "
                "course pattern.\n\n"
                "For full details, visit the "
                "[Freshmen Admissions](https://www.cpp.edu/admissions/"
                "freshmen/index.shtml) page."
            ),
            citations=[
                Citation(
                    title="Freshmen Admissions Requirements",
                    url="https://www.cpp.edu/admissions/freshmen/index.shtml",
                    snippet=(
                        "Cal Poly Pomona accepts applications for fall admission "
                        "from October 1 through December 15."
                    ),
                ),
            ],
        )

    return ChatResponse(
        conversation_id=conversation_id,
        status=ChatStatus.ANSWERED,
        answer_markdown=(
            "Cal Poly Pomona (CPP) is a public polytechnic university in "
            "Pomona, California, and part of the California State University "
            "system. It offers over 90 undergraduate and 30 graduate programs "
            "with an emphasis on **learn-by-doing**."
        ),
        citations=[
            Citation(
                title="About Cal Poly Pomona",
                url="https://www.cpp.edu/about/index.shtml",
                snippet=(
                    "Cal Poly Pomona is a public polytechnic university "
                    "emphasizing learn-by-doing education."
                ),
            ),
        ],
    )
