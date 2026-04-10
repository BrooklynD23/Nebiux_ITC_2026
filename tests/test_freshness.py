"""Unit tests for scripts.preprocess.freshness.

Tests cover:
- compute_outdated_risk() — every risk factor, score thresholds, level mapping
- collect_document_metadata() — output shape and field derivation
- build_topic_key() — canonical key generation
"""

from __future__ import annotations

from typing import Any

import pytest

from scripts.preprocess.filter_corpus import FilterResult
from scripts.preprocess.freshness import (
    build_topic_key,
    collect_document_metadata,
    compute_outdated_risk,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_filter_result(
    *,
    keep: bool = True,
    category: str = "kept",
    is_duplicate: bool = False,
    duplicate_group_size: int = 1,
) -> FilterResult:
    return FilterResult(
        keep=keep,
        category=category,
        is_duplicate=is_duplicate,
        duplicate_group_size=duplicate_group_size,
    )


def _base_metadata(**overrides: Any) -> dict[str, Any]:
    """Return a minimal metadata dict with all fields present."""
    defaults: dict[str, Any] = {
        "filename": "page.md",
        "source_url": "https://www.cpp.edu/page",
        "body_len": 1000,
        "latest_year": None,
        "legacy_url_hits": [],
        "stale_phrase_hits": [],
        "redirect_hint_hits": [],
        "duplicate_group_size": 1,
        "keep": True,
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# compute_outdated_risk — individual risk factors
# ---------------------------------------------------------------------------


class TestComputeOutdatedRiskFactors:
    """Each risk factor is tested in isolation."""

    def test_no_risk_factors_score_zero(self) -> None:
        result = compute_outdated_risk(_base_metadata())
        assert result["outdated_risk_score"] == 0
        assert result["outdated_risk_level"] == "low"
        assert result["risk_reasons"] == []

    def test_legacy_url_adds_3(self) -> None:
        metadata = _base_metadata(legacy_url_hits=["archive"])
        result = compute_outdated_risk(metadata)
        assert result["outdated_risk_score"] == 3
        assert "legacy_url" in result["risk_reasons"]

    def test_stale_language_adds_3(self) -> None:
        metadata = _base_metadata(stale_phrase_hits=["no longer updated"])
        result = compute_outdated_risk(metadata)
        assert result["outdated_risk_score"] == 3
        assert "stale_language" in result["risk_reasons"]

    def test_redirect_language_adds_2(self) -> None:
        metadata = _base_metadata(redirect_hint_hits=["redirect"])
        result = compute_outdated_risk(metadata)
        assert result["outdated_risk_score"] == 2
        assert "redirect_language" in result["risk_reasons"]

    def test_thin_content_adds_1(self) -> None:
        metadata = _base_metadata(body_len=499)
        result = compute_outdated_risk(metadata)
        assert result["outdated_risk_score"] == 1
        assert "thin_content" in result["risk_reasons"]

    def test_body_len_exactly_500_no_thin_penalty(self) -> None:
        metadata = _base_metadata(body_len=500)
        result = compute_outdated_risk(metadata)
        assert "thin_content" not in result["risk_reasons"]

    def test_duplicate_group_adds_1(self) -> None:
        metadata = _base_metadata(duplicate_group_size=3)
        result = compute_outdated_risk(metadata)
        assert result["outdated_risk_score"] == 1
        assert "duplicate_group" in result["risk_reasons"]

    def test_duplicate_group_size_1_no_penalty(self) -> None:
        metadata = _base_metadata(duplicate_group_size=1)
        result = compute_outdated_risk(metadata)
        assert "duplicate_group" not in result["risk_reasons"]

    def test_older_than_peer_one_year_gap_adds_2(self) -> None:
        metadata = _base_metadata(latest_year=2022)
        cluster_context = {"max_latest_year": 2023}
        result = compute_outdated_risk(metadata, cluster_context=cluster_context)
        assert result["outdated_risk_score"] == 2
        assert "older_than_cluster_peer" in result["risk_reasons"]

    def test_older_than_peer_two_year_gap_adds_3(self) -> None:
        metadata = _base_metadata(latest_year=2021)
        cluster_context = {"max_latest_year": 2023}
        result = compute_outdated_risk(metadata, cluster_context=cluster_context)
        assert result["outdated_risk_score"] == 3
        assert "older_than_cluster_peer" in result["risk_reasons"]

    def test_same_year_as_peer_no_penalty(self) -> None:
        metadata = _base_metadata(latest_year=2023)
        cluster_context = {"max_latest_year": 2023}
        result = compute_outdated_risk(metadata, cluster_context=cluster_context)
        assert "older_than_cluster_peer" not in result["risk_reasons"]

    def test_no_latest_year_no_peer_penalty(self) -> None:
        metadata = _base_metadata(latest_year=None)
        cluster_context = {"max_latest_year": 2023}
        result = compute_outdated_risk(metadata, cluster_context=cluster_context)
        assert "older_than_cluster_peer" not in result["risk_reasons"]

    def test_old_explicit_year_three_or_more_years_ago_adds_1(self) -> None:
        metadata = _base_metadata(latest_year=2020)
        cluster_context = {"current_year": 2024}
        result = compute_outdated_risk(metadata, cluster_context=cluster_context)
        assert "old_explicit_year" in result["risk_reasons"]

    def test_old_explicit_year_exactly_3_years_adds_1(self) -> None:
        metadata = _base_metadata(latest_year=2021)
        cluster_context = {"current_year": 2024}
        result = compute_outdated_risk(metadata, cluster_context=cluster_context)
        assert "old_explicit_year" in result["risk_reasons"]

    def test_recent_year_no_old_year_penalty(self) -> None:
        metadata = _base_metadata(latest_year=2023)
        cluster_context = {"current_year": 2024}
        result = compute_outdated_risk(metadata, cluster_context=cluster_context)
        assert "old_explicit_year" not in result["risk_reasons"]

    def test_conflicting_cluster_adds_2(self) -> None:
        metadata = _base_metadata()
        cluster_context = {"cluster_has_conflicts": True}
        result = compute_outdated_risk(metadata, cluster_context=cluster_context)
        assert result["outdated_risk_score"] == 2
        assert "conflicting_cluster" in result["risk_reasons"]

    def test_no_cluster_context_no_conflict_penalty(self) -> None:
        result = compute_outdated_risk(_base_metadata(), cluster_context=None)
        assert "conflicting_cluster" not in result["risk_reasons"]


# ---------------------------------------------------------------------------
# compute_outdated_risk — level thresholds
# ---------------------------------------------------------------------------


class TestComputeOutdatedRiskLevels:
    def test_score_0_is_low(self) -> None:
        result = compute_outdated_risk(_base_metadata())
        assert result["outdated_risk_level"] == "low"

    def test_score_3_is_low(self) -> None:
        # Legacy URL only: +3
        metadata = _base_metadata(legacy_url_hits=["archive"])
        result = compute_outdated_risk(metadata)
        assert result["outdated_risk_score"] == 3
        assert result["outdated_risk_level"] == "low"

    def test_score_4_is_medium(self) -> None:
        # Legacy URL (+3) + thin content (+1) = 4
        metadata = _base_metadata(legacy_url_hits=["archive"], body_len=100)
        result = compute_outdated_risk(metadata)
        assert result["outdated_risk_score"] == 4
        assert result["outdated_risk_level"] == "medium"

    def test_score_7_is_medium(self) -> None:
        # Legacy URL (+3) + stale language (+3) + thin content (+1) = 7
        metadata = _base_metadata(
            legacy_url_hits=["archive"],
            stale_phrase_hits=["deprecated"],
            body_len=100,
        )
        result = compute_outdated_risk(metadata)
        assert result["outdated_risk_score"] == 7
        assert result["outdated_risk_level"] == "medium"

    def test_score_8_is_high(self) -> None:
        # Legacy URL (+3) + stale language (+3) + redirect language (+2) = 8
        metadata = _base_metadata(
            legacy_url_hits=["archive"],
            stale_phrase_hits=["deprecated"],
            redirect_hint_hits=["redirect"],
        )
        result = compute_outdated_risk(metadata)
        assert result["outdated_risk_score"] == 8
        assert result["outdated_risk_level"] == "high"

    def test_newer_candidate_year_returned(self) -> None:
        metadata = _base_metadata(latest_year=2020)
        cluster_context = {"max_latest_year": 2024}
        result = compute_outdated_risk(metadata, cluster_context=cluster_context)
        assert result["newer_candidate_year"] == 2024

    def test_newer_candidate_year_none_when_no_context(self) -> None:
        result = compute_outdated_risk(_base_metadata())
        assert result["newer_candidate_year"] is None


# ---------------------------------------------------------------------------
# collect_document_metadata — output shape
# ---------------------------------------------------------------------------


SAMPLE_BODY = """\
# Financial Aid

Cal Poly Pomona offers financial aid for the 2023-2024 academic year.
Contact finaid@cpp.edu or call (909) 869-3700 for assistance.
Tuition costs $7,460 per year for California residents.
Applications due January 15, 2024.
"""


class TestCollectDocumentMetadata:
    def _call(self, **overrides: Any) -> dict[str, Any]:
        defaults = dict(
            filename="finaid.md",
            source_url="https://www.cpp.edu/financial-aid/index.html",
            cleaned_body=SAMPLE_BODY,
            filter_result=_make_filter_result(),
            alias_count=2,
            file_mtime_iso="2024-01-15T00:00:00Z",
        )
        defaults.update(overrides)
        return collect_document_metadata(**defaults)

    def test_required_keys_present(self) -> None:
        result = self._call()
        expected_keys = {
            "filename",
            "source_url",
            "title",
            "topic_key",
            "body_len",
            "heading_count",
            "latest_year",
            "all_years",
            "date_mentions",
            "contact_emails",
            "contact_phones",
            "money_amounts",
            "stale_phrase_hits",
            "legacy_url_hits",
            "redirect_hint_hits",
            "file_mtime_iso",
            "category",
            "is_duplicate",
            "duplicate_group_size",
            "alias_count",
            "keep",
        }
        assert expected_keys.issubset(result.keys())

    def test_filename_preserved(self) -> None:
        result = self._call()
        assert result["filename"] == "finaid.md"

    def test_source_url_preserved(self) -> None:
        result = self._call()
        assert result["source_url"] == "https://www.cpp.edu/financial-aid/index.html"

    def test_title_extracted_from_h1(self) -> None:
        result = self._call()
        assert result["title"] == "Financial Aid"

    def test_body_len_correct(self) -> None:
        result = self._call()
        assert result["body_len"] == len(SAMPLE_BODY)

    def test_latest_year_extracted(self) -> None:
        result = self._call()
        assert result["latest_year"] == 2024

    def test_all_years_sorted(self) -> None:
        result = self._call()
        assert result["all_years"] == sorted(result["all_years"])

    def test_email_extracted(self) -> None:
        result = self._call()
        assert "finaid@cpp.edu" in result["contact_emails"]

    def test_phone_extracted(self) -> None:
        result = self._call()
        assert "9098693700" in result["contact_phones"]

    def test_money_extracted(self) -> None:
        result = self._call()
        assert any("7,460" in m or "7460" in m for m in result["money_amounts"])

    def test_keep_from_filter_result(self) -> None:
        fr = _make_filter_result(keep=False, category="redirect")
        result = self._call(filter_result=fr)
        assert result["keep"] is False
        assert result["category"] == "redirect"

    def test_duplicate_info_from_filter_result(self) -> None:
        fr = _make_filter_result(is_duplicate=True, duplicate_group_size=4)
        result = self._call(filter_result=fr)
        assert result["is_duplicate"] is True
        assert result["duplicate_group_size"] == 4

    def test_alias_count_preserved(self) -> None:
        result = self._call(alias_count=5)
        assert result["alias_count"] == 5

    def test_file_mtime_iso_preserved(self) -> None:
        result = self._call(file_mtime_iso="2023-06-01T12:00:00Z")
        assert result["file_mtime_iso"] == "2023-06-01T12:00:00Z"

    def test_legacy_url_hits_detected(self) -> None:
        result = self._call(
            source_url="https://www.cpp.edu/archive/old-page",
        )
        assert len(result["legacy_url_hits"]) > 0

    def test_no_legacy_url_hits_on_clean_url(self) -> None:
        result = self._call()
        assert result["legacy_url_hits"] == []

    def test_topic_key_is_nonempty_string(self) -> None:
        result = self._call()
        assert isinstance(result["topic_key"], str)
        assert len(result["topic_key"]) > 0

    def test_heading_count_positive(self) -> None:
        result = self._call()
        assert result["heading_count"] >= 1


# ---------------------------------------------------------------------------
# build_topic_key
# ---------------------------------------------------------------------------


class TestBuildTopicKey:
    def test_basic_key_includes_path_and_title(self) -> None:
        key = build_topic_key("https://www.cpp.edu/admissions/apply", "Apply Now")
        assert "admissions" in key
        assert "apply" in key.lower()

    def test_legacy_tokens_excluded_from_path(self) -> None:
        key = build_topic_key("https://www.cpp.edu/archive/admissions/apply", "Apply")
        # "archive" is a legacy token — should not appear in path root
        assert "archive" not in key

    def test_empty_url_path_uses_root(self) -> None:
        key = build_topic_key("https://www.cpp.edu/", "Home")
        assert "root" in key or len(key) > 0

    def test_same_url_same_title_deterministic(self) -> None:
        key1 = build_topic_key("https://www.cpp.edu/page", "Page Title")
        key2 = build_topic_key("https://www.cpp.edu/page", "Page Title")
        assert key1 == key2

    def test_different_urls_different_keys(self) -> None:
        key1 = build_topic_key("https://www.cpp.edu/admissions", "Admissions")
        key2 = build_topic_key("https://www.cpp.edu/financial-aid", "Financial Aid")
        assert key1 != key2
