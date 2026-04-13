"""Shared fake retriever and runner for API/tool-loop tests."""

from __future__ import annotations

from src.agent.tool_loop import ToolLoopExecution
from src.models import SearchResult
from src.retrieval.interface import RetrieverBase


class FakeRetriever(RetrieverBase):
    """Small deterministic retriever fixture."""

    async def search_corpus(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[SearchResult]:
        del top_k
        normalized = query.lower()

        if "parking" in normalized:
            return [
                SearchResult(
                    chunk_id="parking-001",
                    title="Parking and Transportation",
                    url="https://www.cpp.edu/parking/permits/index.shtml",
                    snippet=(
                        "Parking permits are required on campus Monday through "
                        "Thursday. Students can purchase semester or daily permits "
                        "online through the CPP parking portal."
                    ),
                    score=0.92,
                )
            ]

        if "financial aid" in normalized or "free application for federal student aid" in normalized:
            return [
                SearchResult(
                    chunk_id="aid-001",
                    title="Financial Aid and Scholarships",
                    url="https://www.cpp.edu/financial-aid/index.shtml",
                    snippet=(
                        "CPP offers grants, scholarships, loans, and work-study "
                        "programs. Students must file the FAFSA or CA Dream Act "
                        "Application annually to be considered for financial aid."
                    ),
                    score=0.95,
                )
            ]

        if "admission" in normalized or "apply" in normalized or "deadline" in normalized:
            return [
                SearchResult(
                    chunk_id="admissions-001",
                    title="Freshmen Admissions Requirements",
                    url="https://www.cpp.edu/admissions/freshmen/index.shtml",
                    snippet=(
                        "Cal Poly Pomona accepts applications for fall admission "
                        "from October 1 through December 15."
                    ),
                    score=0.9,
                )
            ]

        if "cal poly pomona" in normalized or "cpp" in normalized:
            return [
                SearchResult(
                    chunk_id="about-001",
                    title="About Cal Poly Pomona",
                    url="https://www.cpp.edu/about/index.shtml",
                    snippet=(
                        "Cal Poly Pomona is a public polytechnic university "
                        "emphasizing learn-by-doing education."
                    ),
                    score=0.88,
                )
            ]

        return []


async def fake_llm_runner(
    message: str,
    history: list[object],
    retriever: RetrieverBase,
) -> ToolLoopExecution:
    """Return a deterministic answer using the fake retriever."""
    del history
    results = await retriever.search_corpus(message, top_k=5)
    if not results:
        return ToolLoopExecution()

    top = results[0]
    if top.title == "Parking and Transportation":
        body = (
            "Parking permits are required on campus Monday through Thursday. "
            "You can purchase semester or daily permits through the CPP parking portal."
        )
    elif top.title == "Financial Aid and Scholarships":
        body = (
            "CPP offers grants, scholarships, loans, and work-study programs. "
            "Students should file the FAFSA or CA Dream Act Application each year "
            "to be considered for financial aid."
        )
    elif top.title == "Freshmen Admissions Requirements":
        body = (
            "Cal Poly Pomona accepts fall admission applications from October 1 "
            "through December 15."
        )
    else:
        body = (
            "Cal Poly Pomona is a public polytechnic university in Pomona, California."
        )

    answer = "\n\n".join(
        [
            body,
            "**Sources:**",
            f"- [{top.title}]({top.url}): {top.snippet}",
        ]
    )
    return ToolLoopExecution(answer_markdown=answer, retrieved=results)
