"""Stub retrieval backend returning mock results for Sprint 0/1 development."""

from __future__ import annotations

from src.models import SearchResult
from src.retrieval.interface import RetrieverBase

# Pre-built mock results that cover several CPP topics
_MOCK_RESULTS: list[dict[str, object]] = [
    {
        "chunk_id": "admissions-freshmen-001",
        "title": "Freshmen Admissions Requirements",
        "url": "https://www.cpp.edu/admissions/freshmen/index.shtml",
        "snippet": (
            "Cal Poly Pomona accepts applications for fall admission from "
            "October 1 through December 15. Applicants must meet CSU "
            "eligibility requirements including completion of A-G courses."
        ),
        "score": 0.92,
    },
    {
        "chunk_id": "housing-overview-001",
        "title": "University Housing Overview",
        "url": "https://www.cpp.edu/housing/index.shtml",
        "snippet": (
            "Cal Poly Pomona offers on-campus housing options including "
            "traditional residence halls and suite-style living. First-year "
            "students are guaranteed housing if they apply by the deadline."
        ),
        "score": 0.87,
    },
    {
        "chunk_id": "cs-major-001",
        "title": "Computer Science B.S. Program",
        "url": "https://www.cpp.edu/sci/computer-science/index.shtml",
        "snippet": (
            "The Computer Science program at Cal Poly Pomona emphasizes "
            "hands-on learning through lab courses and senior projects. "
            "Students complete 180 quarter units including core CS courses."
        ),
        "score": 0.85,
    },
    {
        "chunk_id": "financial-aid-001",
        "title": "Financial Aid and Scholarships",
        "url": "https://www.cpp.edu/financial-aid/index.shtml",
        "snippet": (
            "CPP offers grants, scholarships, loans, and work-study programs. "
            "Students must file the FAFSA or CA Dream Act Application annually "
            "to be considered for financial aid."
        ),
        "score": 0.80,
    },
    {
        "chunk_id": "parking-permits-001",
        "title": "Parking and Transportation",
        "url": "https://www.cpp.edu/parking/permits/index.shtml",
        "snippet": (
            "Parking permits are required on campus Monday through Thursday. "
            "Students can purchase semester or daily permits online through "
            "the CPP parking portal."
        ),
        "score": 0.75,
    },
]


class StubRetriever(RetrieverBase):
    """Return hardcoded mock results for development and testing."""

    async def search_corpus(
        self, query: str, top_k: int = 5
    ) -> list[SearchResult]:
        """Return up to *top_k* mock results regardless of query content."""
        results = _MOCK_RESULTS[:top_k]
        return [SearchResult(**item) for item in results]
