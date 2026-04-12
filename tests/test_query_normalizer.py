"""Tests for retrieval-oriented query normalization."""

from __future__ import annotations

from src.agent.query_normalizer import normalize


class TestNormalize:
    """Validate the normalization pipeline and ambiguity heuristics."""

    def test_lowercase_and_strip_whitespace(self) -> None:
        normalized = normalize("  FAFSA DUE WHEN?? ")

        assert (
            normalized.normalized_text
            == "Free Application for Federal Student Aid due when"
        )
        assert normalized.is_ambiguous is False

    def test_abbreviation_expansion_multi_token_query(self) -> None:
        normalized = normalize("cpp admissions")

        assert normalized.normalized_text == "Cal Poly Pomona admissions"

    def test_filler_phrase_strip(self) -> None:
        normalized = normalize("can you tell me about parking")

        assert normalized.normalized_text == "about parking"

    def test_punctuation_normalization(self) -> None:
        normalized = normalize("what is fafsa???")

        assert "???" not in normalized.normalized_text
        assert (
            normalized.normalized_text
            == "what is Free Application for Federal Student Aid"
        )

    def test_ambiguous_single_token_pre_expansion(self) -> None:
        normalized = normalize("cpp")

        assert normalized.normalized_text == "Cal Poly Pomona"
        assert normalized.is_ambiguous is True

    def test_ambiguous_two_tokens_pre_expansion(self) -> None:
        normalized = normalize("fafsa deadline")

        assert normalized.is_ambiguous is True

    def test_not_ambiguous_three_tokens_pre_expansion(self) -> None:
        normalized = normalize("fafsa deadline cpp")

        assert normalized.is_ambiguous is False

    def test_filler_only_becomes_empty_and_ambiguous(self) -> None:
        normalized = normalize("can you tell me")

        assert normalized.normalized_text == ""
        assert normalized.is_ambiguous is True

    def test_original_field_preserved(self) -> None:
        normalized = normalize("  FAFSA DUE WHEN?? ")

        assert normalized.original == "  FAFSA DUE WHEN?? "
