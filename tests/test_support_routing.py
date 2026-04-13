"""Tests for deterministic support routing before the LLM tool loop."""

from __future__ import annotations

import pytest

from src.agent.support_routing import classify_support_route
from src.agent.tool_loop import run_tool_loop
from src.models import SearchResult
from src.retrieval.interface import RetrieverBase


class _SupportRetriever(RetrieverBase):
    async def search_corpus(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[SearchResult]:
        del top_k
        normalized = query.lower()

        if "caps" in normalized:
            return [
                SearchResult(
                    chunk_id="caps-001",
                    title="Counseling and Psychological Services",
                    url="https://www.cpp.edu/campus-life/index.shtml",
                    snippet=(
                        "Counseling and Psychological Services (CAPS) is a "
                        "confidential, comprehensive, short-term mental health "
                        "facility with licensed mental health clinicians."
                    ),
                    score=0.97,
                )
            ]

        if "student health" in normalized:
            return [
                SearchResult(
                    chunk_id="health-001",
                    title="Student Health Services",
                    url="https://www.cpp.edu/campus-life/index.shtml",
                    snippet=(
                        "Student Health Services provides Cal Poly Pomona "
                        "students with affordable, accessible and high-quality "
                        "health care."
                    ),
                    score=0.96,
                )
            ]

        if "university police" in normalized or "police" in normalized:
            return [
                SearchResult(
                    chunk_id="police-001",
                    title="University Police",
                    url="https://www.cpp.edu/~police/index.shtml",
                    snippet=(
                        "For Police, Medical, Fire or other emergencies, dial "
                        "9-1-1 from any campus or blue emergency phone. If using "
                        "a cell phone, dial (909) 869-3070."
                    ),
                    score=0.99,
                )
            ]

        if "care center" in normalized:
            return [
                SearchResult(
                    chunk_id="care-001",
                    title="Care Center",
                    url="https://www.cpp.edu/campus-life/index.shtml",
                    snippet=(
                        "The Care Center is the first place to send students who "
                        "are of concern or in distress. We connect students to "
                        "resources they need to succeed and offer Basic Needs "
                        "services."
                    ),
                    score=0.95,
                )
            ]

        return []


@pytest.mark.parametrize(
    ("message", "expected_route"),
    [
        ("I feel depressed and overwhelmed. Where do I go?", "caps"),
        ("I fell and need help right now", "student_health"),
        (
            "Somebody is getting mugged in parking lot M. Get help!",
            "university_police",
        ),
        (
            "My parents cannot work and I need help paying for school and "
            "caring for my siblings",
            "care_center",
        ),
    ],
)
def test_classify_support_route_matches_expected_route(
    message: str,
    expected_route: str,
) -> None:
    route = classify_support_route(message)

    assert route is not None
    assert route.route_id == expected_route


def test_classify_support_route_ignores_normal_cpp_questions() -> None:
    route = classify_support_route("How do I apply for financial aid at CPP?")

    assert route is None


def test_classify_support_route_does_not_overmatch_fell_behind() -> None:
    route = classify_support_route("I fell behind in class and need tutoring")

    assert route is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("message", "expected_title"),
    [
        (
            "I feel depressed and overwhelmed. Where do I go?",
            "Counseling and Psychological Services",
        ),
        ("I fell and need help right now", "Student Health Services"),
        ("Somebody is getting mugged in parking lot M. Get help!", "University Police"),
        (
            "My parents cannot work and I need help paying for school and "
            "caring for my siblings",
            "Care Center",
        ),
    ],
)
async def test_run_tool_loop_returns_cited_service_referral_without_llm(
    message: str,
    expected_title: str,
) -> None:
    async def _should_not_run(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("LLM runner should not be invoked for support routes")

    response = await run_tool_loop(
        message=message,
        retriever=_SupportRetriever(),
        llm_runner=_should_not_run,
    )

    assert response.status.value == "answered"
    assert expected_title in response.answer_markdown
    assert len(response.citations) == 1
    assert response.citations[0].title == expected_title
