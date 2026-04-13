"""Deterministic routing for urgent or high-support student requests."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.models import ChatResponse, ChatStatus, Citation, SearchResult


@dataclass(frozen=True)
class SupportRoute:
    """A pre-LLM routed support destination."""

    route_id: str
    retrieval_query: str
    lead_text: str


_POLICE_PATTERNS = (
    re.compile(r"\bmugged\b", re.IGNORECASE),
    re.compile(r"\bmugging\b", re.IGNORECASE),
    re.compile(r"\bassault(?:ed)?\b", re.IGNORECASE),
    re.compile(r"\brob(?:bed|bery)?\b", re.IGNORECASE),
    re.compile(r"\bactive danger\b", re.IGNORECASE),
    re.compile(r"\bemergency\b", re.IGNORECASE),
)
_HEALTH_PATTERNS = (
    re.compile(r"\bi fell(?:\s+(?:and|down|off|on|over)\b|$)", re.IGNORECASE),
    re.compile(r"\binjur(?:ed|y)\b", re.IGNORECASE),
    re.compile(r"\bhurt\b", re.IGNORECASE),
    re.compile(r"\bfeel sick\b", re.IGNORECASE),
    re.compile(r"\bsick on campus\b", re.IGNORECASE),
    re.compile(r"\bneed medical help\b", re.IGNORECASE),
)
_CAPS_PATTERNS = (
    re.compile(r"\bdepress(?:ed|ion)?\b", re.IGNORECASE),
    re.compile(r"\banx(?:ious|iety)\b", re.IGNORECASE),
    re.compile(r"\bpanic\b", re.IGNORECASE),
    re.compile(r"\bmental health\b", re.IGNORECASE),
    re.compile(r"\boverwhelmed\b", re.IGNORECASE),
    re.compile(r"\bdistress\b", re.IGNORECASE),
)
_CARE_CENTER_PATTERNS = (
    re.compile(r"\bparents?\b.*\bunable to work\b", re.IGNORECASE),
    re.compile(r"\b(can(?:not|'t)|cannot)\s+afford\b", re.IGNORECASE),
    re.compile(r"\b(can(?:not|'t)|cannot)\s+pay\b", re.IGNORECASE),
    re.compile(r"\bpay(?:ing)? for school\b", re.IGNORECASE),
    re.compile(r"\b(can(?:not|'t)|cannot)\s+afford classes\b", re.IGNORECASE),
    re.compile(r"\bbasic needs\b", re.IGNORECASE),
    re.compile(r"\bsiblings?\b", re.IGNORECASE),
    re.compile(r"\bfinancial hardship\b", re.IGNORECASE),
    re.compile(r"\bfood support\b", re.IGNORECASE),
)

_ROUTES = (
    (
        _POLICE_PATTERNS,
        SupportRoute(
            route_id="university_police",
            retrieval_query="university police emergency campus safety",
            lead_text=(
                "This sounds like an urgent campus safety issue. Start with "
                "**University Police** right away."
            ),
        ),
    ),
    (
        _HEALTH_PATTERNS,
        SupportRoute(
            route_id="student_health",
            retrieval_query="student health services medical help on campus",
            lead_text=(
                "This sounds like a medical or injury-related issue. Start with "
                "**Student Health Services**."
            ),
        ),
    ),
    (
        _CAPS_PATTERNS,
        SupportRoute(
            route_id="caps",
            retrieval_query="counseling and psychological services caps",
            lead_text=(
                "For mental health or emotional distress support, start with "
                "**Counseling and Psychological Services (CAPS)**."
            ),
        ),
    ),
    (
        _CARE_CENTER_PATTERNS,
        SupportRoute(
            route_id="care_center",
            retrieval_query="care center basic needs distress support",
            lead_text=(
                "For hardship, crisis support, or basic-needs help, start with "
                "**the Care Center**."
            ),
        ),
    ),
)


def classify_support_route(message: str) -> SupportRoute | None:
    """Classify whether a message should bypass the normal LLM flow."""
    for patterns, route in _ROUTES:
        if any(pattern.search(message) for pattern in patterns):
            return route
    return None


def build_support_response(
    conversation_id: str,
    route: SupportRoute,
    results: list[SearchResult],
) -> ChatResponse:
    """Build a deterministic cited response for a routed support request."""
    top_result = results[0]
    answer_markdown = "\n\n".join(
        [
            route.lead_text,
            f"CPP points students to **{top_result.title}**.",
            f"> {top_result.snippet}",
        ]
    )

    return ChatResponse(
        conversation_id=conversation_id,
        status=ChatStatus.ANSWERED,
        answer_markdown=answer_markdown,
        citations=[
            Citation(
                title=top_result.title,
                url=top_result.url,
                snippet=top_result.snippet,
            )
        ],
    )
