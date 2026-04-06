"""Stub tool loop for the LLM agent.

In Sprint 2 this will contain the real tool-calling loop that:
1. Sends user message + conversation history to the LLM
2. Detects tool_call requests for ``search_corpus``
3. Executes retrieval, feeds results back to the LLM
4. Returns the final grounded answer with citations

For Sprint 0-1, this returns a realistic mock response so the API
contract can be validated end-to-end.
"""

from __future__ import annotations

import uuid

from src.models import ChatResponse, ChatStatus, Citation


async def run_tool_loop(
    message: str,
    conversation_id: str | None = None,
) -> ChatResponse:
    """Process a user message through the (stubbed) agent tool loop.

    Parameters
    ----------
    message:
        The user's natural-language question.
    conversation_id:
        Existing conversation UUID, or None to start fresh.

    Returns
    -------
    ChatResponse
        A mock response conforming to the POST /chat contract.
    """
    cid = conversation_id or str(uuid.uuid4())

    # Simple keyword-based stub routing for realistic mock behavior
    lower = message.lower()

    if any(kw in lower for kw in ("parking", "permit", "transportation")):
        return ChatResponse(
            conversation_id=cid,
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
            conversation_id=cid,
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

    # Default: a generic answered response
    return ChatResponse(
        conversation_id=cid,
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
