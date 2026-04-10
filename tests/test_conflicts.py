"""Unit tests for scripts.preprocess.conflicts.

Tests cover:
- detect_cluster_conflicts() — grouping, conflict detection per field, newer-candidate selection
- format_conflict_report() — markdown structure and content
"""

from __future__ import annotations

from typing import Any

import pytest

from scripts.preprocess.conflicts import detect_cluster_conflicts, format_conflict_report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_record(
    filename: str,
    topic_key: str,
    *,
    keep: bool = True,
    latest_year: int | None = None,
    contact_emails: list[str] | None = None,
    contact_phones: list[str] | None = None,
    money_amounts: list[str] | None = None,
    date_mentions: list[str] | None = None,
    legacy_url_hits: list[str] | None = None,
    source_url: str = "https://www.cpp.edu/page",
) -> dict[str, Any]:
    return {
        "filename": filename,
        "topic_key": topic_key,
        "source_url": source_url,
        "keep": keep,
        "latest_year": latest_year,
        "contact_emails": contact_emails or [],
        "contact_phones": contact_phones or [],
        "money_amounts": money_amounts or [],
        "date_mentions": date_mentions or [],
        "legacy_url_hits": legacy_url_hits or [],
    }


# ---------------------------------------------------------------------------
# detect_cluster_conflicts
# ---------------------------------------------------------------------------


class TestDetectClusterConflicts:
    def test_empty_records_returns_empty(self) -> None:
        assert detect_cluster_conflicts([]) == []

    def test_single_record_per_topic_no_conflicts(self) -> None:
        records = [_make_record("a.md", "admissions__apply")]
        assert detect_cluster_conflicts(records) == []

    def test_two_identical_records_no_conflicts(self) -> None:
        records = [
            _make_record("a.md", "topic__key", latest_year=2023, contact_emails=["x@cpp.edu"]),
            _make_record("b.md", "topic__key", latest_year=2023, contact_emails=["x@cpp.edu"]),
        ]
        assert detect_cluster_conflicts(records) == []

    def test_year_conflict_detected(self) -> None:
        records = [
            _make_record("old.md", "aid__apply", latest_year=2021),
            _make_record("new.md", "aid__apply", latest_year=2024),
        ]
        result = detect_cluster_conflicts(records)
        assert len(result) == 1
        assert "latest_year" in result[0]["conflict_fields"]

    def test_email_conflict_detected(self) -> None:
        records = [
            _make_record("a.md", "topic__key", contact_emails=["old@cpp.edu"]),
            _make_record("b.md", "topic__key", contact_emails=["new@cpp.edu"]),
        ]
        result = detect_cluster_conflicts(records)
        assert len(result) == 1
        assert "contact_emails" in result[0]["conflict_fields"]

    def test_phone_conflict_detected(self) -> None:
        records = [
            _make_record("a.md", "topic__key", contact_phones=["9098691111"]),
            _make_record("b.md", "topic__key", contact_phones=["9098692222"]),
        ]
        result = detect_cluster_conflicts(records)
        assert "contact_phones" in result[0]["conflict_fields"]

    def test_money_conflict_detected(self) -> None:
        records = [
            _make_record("a.md", "topic__key", money_amounts=["$1,000"]),
            _make_record("b.md", "topic__key", money_amounts=["$2,000"]),
        ]
        result = detect_cluster_conflicts(records)
        assert "money_amounts" in result[0]["conflict_fields"]

    def test_date_conflict_detected(self) -> None:
        records = [
            _make_record("a.md", "topic__key", date_mentions=["January 1, 2022"]),
            _make_record("b.md", "topic__key", date_mentions=["March 15, 2024"]),
        ]
        result = detect_cluster_conflicts(records)
        assert "date_mentions" in result[0]["conflict_fields"]

    def test_filtered_records_excluded(self) -> None:
        records = [
            _make_record("a.md", "topic__key", keep=False, latest_year=2021),
            _make_record("b.md", "topic__key", keep=False, latest_year=2024),
        ]
        # Both excluded → no cluster to compare
        assert detect_cluster_conflicts(records) == []

    def test_mixed_keep_only_kept_compared(self) -> None:
        records = [
            _make_record("kept.md", "topic__key", keep=True, latest_year=2023),
            _make_record("removed.md", "topic__key", keep=False, latest_year=2019),
        ]
        # Only one kept record — can't form a conflict cluster
        assert detect_cluster_conflicts(records) == []

    def test_cluster_size_correct(self) -> None:
        records = [
            _make_record("a.md", "topic__key", latest_year=2020),
            _make_record("b.md", "topic__key", latest_year=2022),
            _make_record("c.md", "topic__key", latest_year=2024),
        ]
        result = detect_cluster_conflicts(records)
        assert result[0]["cluster_size"] == 3

    def test_filenames_all_included(self) -> None:
        records = [
            _make_record("a.md", "topic__key", latest_year=2020),
            _make_record("b.md", "topic__key", latest_year=2024),
        ]
        result = detect_cluster_conflicts(records)
        assert set(result[0]["filenames"]) == {"a.md", "b.md"}

    def test_newer_candidate_is_highest_year(self) -> None:
        records = [
            _make_record("old.md", "topic__key", latest_year=2019),
            _make_record("new.md", "topic__key", latest_year=2024),
        ]
        result = detect_cluster_conflicts(records)
        assert result[0]["newer_candidate_filename"] == "new.md"
        assert result[0]["newer_candidate_year"] == 2024

    def test_newer_candidate_prefers_fewer_legacy_hits(self) -> None:
        # Same year — legacy URL hits break the tie (fewer is better)
        records = [
            _make_record("clean.md", "topic__key", latest_year=2023, legacy_url_hits=[]),
            _make_record("legacy.md", "topic__key", latest_year=2023, legacy_url_hits=["archive"]),
        ]
        # Add a field difference so a conflict is detected
        records[0]["contact_emails"] = ["a@cpp.edu"]
        records[1]["contact_emails"] = ["b@cpp.edu"]
        result = detect_cluster_conflicts(records)
        assert result[0]["newer_candidate_filename"] == "clean.md"

    def test_sorted_by_cluster_size_descending(self) -> None:
        records = [
            # Small cluster (2 records) with conflict
            _make_record("x1.md", "small__topic", latest_year=2020),
            _make_record("x2.md", "small__topic", latest_year=2023),
            # Large cluster (3 records) with conflict
            _make_record("y1.md", "large__topic", latest_year=2019),
            _make_record("y2.md", "large__topic", latest_year=2021),
            _make_record("y3.md", "large__topic", latest_year=2024),
        ]
        result = detect_cluster_conflicts(records)
        assert len(result) == 2
        assert result[0]["cluster_size"] >= result[1]["cluster_size"]

    def test_multiple_independent_clusters(self) -> None:
        records = [
            _make_record("a.md", "topic_a", latest_year=2020),
            _make_record("b.md", "topic_a", latest_year=2024),
            _make_record("c.md", "topic_b", contact_emails=["x@cpp.edu"]),
            _make_record("d.md", "topic_b", contact_emails=["y@cpp.edu"]),
        ]
        result = detect_cluster_conflicts(records)
        assert len(result) == 2

    def test_conflict_fields_sorted(self) -> None:
        records = [
            _make_record("a.md", "topic__key", latest_year=2020, contact_emails=["a@cpp.edu"]),
            _make_record("b.md", "topic__key", latest_year=2024, contact_emails=["b@cpp.edu"]),
        ]
        result = detect_cluster_conflicts(records)
        fields = result[0]["conflict_fields"]
        assert fields == sorted(fields)

    def test_empty_list_values_not_treated_as_conflict(self) -> None:
        """Documents where one has no emails and one has no emails should not conflict."""
        records = [
            _make_record("a.md", "topic__key", latest_year=2020, contact_emails=[]),
            _make_record("b.md", "topic__key", latest_year=2024, contact_emails=[]),
        ]
        result = detect_cluster_conflicts(records)
        # Only latest_year should be a conflict field
        assert result[0]["conflict_fields"] == ["latest_year"]


# ---------------------------------------------------------------------------
# format_conflict_report
# ---------------------------------------------------------------------------


class TestFormatConflictReport:
    def _make_cluster(self, topic_key: str = "topic__key", size: int = 2) -> dict[str, Any]:
        filenames = [f"file{i}.md" for i in range(size)]
        urls = [f"https://www.cpp.edu/page{i}" for i in range(size)]
        return {
            "topic_key": topic_key,
            "cluster_size": size,
            "filenames": filenames,
            "source_urls": urls,
            "conflict_fields": ["latest_year", "contact_emails"],
            "newer_candidate_filename": filenames[0],
            "newer_candidate_year": 2024,
        }

    def test_report_starts_with_h1(self) -> None:
        report = format_conflict_report([], {})
        assert report.startswith("# Conflict Review Report")

    def test_empty_clusters_message(self) -> None:
        report = format_conflict_report([], {"total_kept": 100})
        assert "No conflicts detected" in report

    def test_cluster_count_in_report(self) -> None:
        clusters = [self._make_cluster("a__key"), self._make_cluster("b__key")]
        report = format_conflict_report(clusters, {"total_kept": 200})
        assert "2" in report  # 2 conflict clusters

    def test_topic_key_appears_in_report(self) -> None:
        clusters = [self._make_cluster("admissions__apply")]
        report = format_conflict_report(clusters, {})
        assert "admissions__apply" in report

    def test_filenames_appear_in_report(self) -> None:
        clusters = [self._make_cluster()]
        report = format_conflict_report(clusters, {})
        assert "file0.md" in report
        assert "file1.md" in report

    def test_conflict_fields_appear_in_report(self) -> None:
        clusters = [self._make_cluster()]
        report = format_conflict_report(clusters, {})
        assert "latest_year" in report
        assert "contact_emails" in report

    def test_newer_candidate_appears_in_report(self) -> None:
        clusters = [self._make_cluster()]
        report = format_conflict_report(clusters, {})
        assert "file0.md" in report

    def test_newer_candidate_year_appears_in_report(self) -> None:
        clusters = [self._make_cluster()]
        report = format_conflict_report(clusters, {})
        assert "2024" in report

    def test_stats_total_kept_in_report(self) -> None:
        report = format_conflict_report([], {"total_kept": 7388, "total_records": 8042})
        assert "7388" in report
        assert "8042" in report

    def test_multiple_clusters_all_appear(self) -> None:
        clusters = [
            self._make_cluster("alpha__topic"),
            self._make_cluster("beta__topic"),
        ]
        report = format_conflict_report(clusters, {})
        assert "alpha__topic" in report
        assert "beta__topic" in report

    def test_returns_string(self) -> None:
        report = format_conflict_report([], {})
        assert isinstance(report, str)
