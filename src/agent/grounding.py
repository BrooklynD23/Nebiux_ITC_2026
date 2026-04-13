"""Grounding confidence assessment and weak-retrieval refusal helpers."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Literal, Protocol

from src.models import ChatResponse, ChatStatus, SearchResult

ScoreAggregation = Literal["max", "mean_top3", "count_only"]


@dataclass(frozen=True)
class GroundingConfig:
    """Threshold configuration for retrieval grounding checks."""

    min_top_score: float = 0.3
    min_results: int = 1
    score_aggregation: ScoreAggregation = "max"
    expected_top_k: int = 5

    def __post_init__(self) -> None:
        if not 0.0 <= self.min_top_score <= 1.0:
            raise ValueError("min_top_score must be between 0.0 and 1.0")
        if self.min_results < 1:
            raise ValueError("min_results must be >= 1")
        if self.expected_top_k < 1:
            raise ValueError("expected_top_k must be >= 1")


@dataclass(frozen=True)
class GroundingVerdict:
    """Outcome from confidence assessment over retrieval results."""

    grounded: bool
    confidence_score: float
    reason: str
    qualifying_results: int
    total_results: int


@dataclass(frozen=True)
class RefusalContext:
    """Context used to build user-facing not-found refusal copy."""

    normalized_query: str


def assess_confidence(
    results: list[SearchResult],
    config: GroundingConfig = GroundingConfig(),
) -> GroundingVerdict:
    """Assess whether retrieval is strong enough to attempt an answer."""
    if not results:
        return GroundingVerdict(
            grounded=False,
            confidence_score=0.0,
            reason="weak_retrieval.no_results",
            qualifying_results=0,
            total_results=0,
        )

    if config.score_aggregation == "count_only":
        confidence = min(1.0, len(results) / config.expected_top_k)
        grounded = len(results) >= config.min_results
        return GroundingVerdict(
            grounded=grounded,
            confidence_score=confidence,
            reason="passed" if grounded else "weak_retrieval.insufficient_results",
            qualifying_results=len(results),
            total_results=len(results),
        )

    qualifying = [result for result in results if result.score >= config.min_top_score]
    confidence = _compute_confidence(results, config.score_aggregation)

    grounded = len(qualifying) >= config.min_results
    return GroundingVerdict(
        grounded=grounded,
        confidence_score=confidence,
        reason="passed"
        if grounded
        else "weak_retrieval.insufficient_qualifying_results",
        qualifying_results=len(qualifying),
        total_results=len(results),
    )


def build_refusal_response(
    conversation_id: str,
    verdict: GroundingVerdict,
    context: RefusalContext,
) -> ChatResponse:
    """Build a standardized weak-retrieval response for `/chat`."""
    query = _format_query(context.normalized_query)
    answer_markdown = (
        f"I couldn't find enough reliable information on the CPP website for "
        f'"{query}". Please check [cpp.edu](https://www.cpp.edu) directly '
        "or contact the relevant office."
    )
    return ChatResponse(
        conversation_id=conversation_id,
        status=ChatStatus.NOT_FOUND,
        answer_markdown=answer_markdown,
        citations=[],
    )


class PostHocValidator(Protocol):
    """Future interface for answer-vs-chunk grounding validation."""

    def validate(
        self,
        answer: str,
        chunks: list[SearchResult],
    ) -> GroundingVerdict: ...


class NoOpValidator:
    """Placeholder validator that always passes."""

    def validate(
        self,
        answer: str,
        chunks: list[SearchResult],
    ) -> GroundingVerdict:
        del answer
        return GroundingVerdict(
            grounded=True,
            confidence_score=1.0,
            reason="post_hoc.not_implemented",
            qualifying_results=len(chunks),
            total_results=len(chunks),
        )


def _compute_confidence(
    results: list[SearchResult],
    aggregation: ScoreAggregation,
) -> float:
    if aggregation == "max":
        return max(result.score for result in results)
    if aggregation == "mean_top3":
        top_scores = sorted(
            (result.score for result in results),
            reverse=True,
        )[:3]
        return mean(top_scores)
    raise ValueError(f"Unknown aggregation mode: {aggregation}")


def _format_query(query: str) -> str:
    normalized = " ".join(query.split())
    if not normalized:
        return "your request"
    max_len = 120
    if len(normalized) <= max_len:
        return normalized
    return normalized[: max_len - 1].rstrip() + "..."
