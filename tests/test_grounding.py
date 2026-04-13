"""Unit tests for grounding confidence and refusal helpers."""

from __future__ import annotations

import pytest

from src.agent.grounding import (
    GroundingConfig,
    NoOpValidator,
    RefusalContext,
    assess_confidence,
    build_refusal_response,
)
from src.models import ChatStatus, SearchResult


def _result(score: float, *, chunk_id: str = "chunk-1") -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        title="Title",
        url="https://www.cpp.edu/example",
        snippet="Snippet",
        score=score,
    )


def test_assess_confidence_empty_results() -> None:
    verdict = assess_confidence([])

    assert verdict.grounded is False
    assert verdict.confidence_score == 0.0
    assert verdict.reason == "weak_retrieval.no_results"


def test_assess_confidence_single_low_score_not_grounded() -> None:
    verdict = assess_confidence([_result(0.1)])

    assert verdict.grounded is False
    assert verdict.confidence_score == 0.1


def test_assess_confidence_high_score_grounded() -> None:
    verdict = assess_confidence([_result(0.8)])

    assert verdict.grounded is True
    assert verdict.confidence_score == 0.8
    assert verdict.reason == "passed"


def test_assess_confidence_mean_top3_aggregation() -> None:
    verdict = assess_confidence(
        [_result(0.9), _result(0.8), _result(0.7), _result(0.1)],
        GroundingConfig(score_aggregation="mean_top3"),
    )

    assert verdict.grounded is True
    assert verdict.confidence_score == pytest.approx(0.8)


def test_assess_confidence_count_only_mode() -> None:
    verdict = assess_confidence(
        [_result(0.1), _result(0.2), _result(0.0)],
        GroundingConfig(
            score_aggregation="count_only",
            min_results=3,
            expected_top_k=5,
        ),
    )

    assert verdict.grounded is True
    assert verdict.confidence_score == pytest.approx(0.6)


def test_assess_confidence_dynamic_invalid_aggregation_raises() -> None:
    config = GroundingConfig()
    object.__setattr__(config, "score_aggregation", "bad")

    with pytest.raises(ValueError, match="Unknown aggregation mode"):
        assess_confidence([_result(0.8)], config=config)  # type: ignore[arg-type]


def test_build_refusal_response_mentions_query() -> None:
    verdict = assess_confidence([])
    response = build_refusal_response(
        conversation_id="cid-123",
        verdict=verdict,
        context=RefusalContext(normalized_query="fafsa deadline cpp"),
    )

    assert response.status == ChatStatus.NOT_FOUND
    assert response.citations == []
    assert "fafsa deadline cpp" in response.answer_markdown


def test_noop_validator_always_passes() -> None:
    verdict = NoOpValidator().validate(
        answer="test",
        chunks=[_result(0.2)],
    )

    assert verdict.grounded is True
    assert verdict.confidence_score == 1.0
