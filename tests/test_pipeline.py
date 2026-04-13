"""Integration tests for the preprocessing pipeline.

Creates a temporary mini-corpus and runs the full pipeline against it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.preprocess.run_pipeline import run_pipeline


@pytest.fixture
def mini_corpus(tmp_path: Path) -> Path:
    """Create a tiny corpus with known content for testing."""
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()

    # Good page — should survive
    (corpus_dir / "admissions.md").write_text(
        """\
[Skip to Content]

[Cal Poly Pomona]

# Admissions

The Office of Admissions at Cal Poly Pomona welcomes applications from
first-time freshmen, transfer students, and international students.
Our admissions process is designed to be straightforward and supportive.

## Requirements

Applicants must complete the A-G requirements with a minimum GPA of 2.0.
Transfer students need at least 60 semester units of transferable coursework.

## Deadlines

| Period | Open | Close |
|--------|------|-------|
| Fall   | Oct  | Dec   |
| Spring | Aug  | Aug   |

© 2024 Cal Poly Pomona
""",
        encoding="utf-8",
    )

    # Redirect page — should be excluded
    (corpus_dir / "old_page.md").write_text(
        "You are being redirected to the new page.\n\nClick here if not redirected.",
        encoding="utf-8",
    )

    # Login-gated page — should be excluded
    (corpus_dir / "portal.md").write_text(
        "Please log in to access BroncoDirect.\n\nSSO Login required.",
        encoding="utf-8",
    )

    # Too-short page — should be excluded after cleaning
    (corpus_dir / "tiny.md").write_text(
        "[Skip to Content]\n\n[Cal Poly Pomona]\n\nHello.\n\n© 2024",
        encoding="utf-8",
    )

    # index.json
    index = {
        "https://www.cpp.edu/admissions/index.shtml": "admissions.md",
        "https://www.cpp.edu/old": "old_page.md",
        "https://www.cpp.edu/portal": "portal.md",
        "https://www.cpp.edu/tiny": "tiny.md",
    }
    (corpus_dir / "index.json").write_text(
        json.dumps(index), encoding="utf-8"
    )

    return corpus_dir


def test_pipeline_produces_expected_outputs(
    mini_corpus: Path, tmp_path: Path
) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    report = run_pipeline(mini_corpus, output_dir)

    # Check report counts
    assert report.total_source_files == 4
    assert report.kept == 1  # only admissions.md
    assert report.excluded == 3

    # Check output files exist
    assert (output_dir / "cleaned" / "admissions.md").is_file()
    assert (output_dir / "metadata.json").is_file()
    assert (output_dir / "filter_report.json").is_file()
    assert (output_dir / "freshness_manifest.json").is_file()
    assert (output_dir / "conflict_review.md").is_file()

    # Verify excluded files are NOT in cleaned/
    assert not (output_dir / "cleaned" / "old_page.md").exists()
    assert not (output_dir / "cleaned" / "portal.md").exists()
    assert not (output_dir / "cleaned" / "tiny.md").exists()


def test_pipeline_metadata_structure(
    mini_corpus: Path, tmp_path: Path
) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    run_pipeline(mini_corpus, output_dir)

    metadata = json.loads((output_dir / "metadata.json").read_text())
    assert isinstance(metadata, list)
    assert len(metadata) == 1

    entry = metadata[0]
    assert entry["source_file"] == "admissions.md"
    assert entry["cleaned_file"] == "admissions.md"
    assert entry["title"] == "Admissions"
    assert entry["url"] == "https://www.cpp.edu/admissions/index.shtml"
    assert entry["word_count"] > 30
    assert entry["heading_count"] >= 2
    assert isinstance(entry["quality_flags"], list)


def test_pipeline_freshness_manifest_structure(
    mini_corpus: Path, tmp_path: Path
) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    run_pipeline(mini_corpus, output_dir)

    manifest = json.loads((output_dir / "freshness_manifest.json").read_text())
    assert isinstance(manifest, list)
    assert len(manifest) == 1

    entry = manifest[0]
    assert entry["filename"] == "admissions.md"
    assert entry["keep"] is True
    assert entry["alias_count"] == 1
    assert entry["outdated_risk_level"] in {"low", "medium", "high"}
    assert "outdated_risk_score" in entry
    assert isinstance(entry["risk_reasons"], list)
    assert "file_mtime_iso" in entry


def test_pipeline_conflict_review_structure(
    mini_corpus: Path, tmp_path: Path
) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    run_pipeline(mini_corpus, output_dir)

    report = (output_dir / "conflict_review.md").read_text()
    assert report.startswith("# Conflict Review Report")
    assert "No conflicts detected" in report


def test_pipeline_filter_report_structure(
    mini_corpus: Path, tmp_path: Path
) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    run_pipeline(mini_corpus, output_dir)

    report = json.loads((output_dir / "filter_report.json").read_text())
    assert report["total_source_files"] == 4
    assert report["kept"] == 1
    assert report["excluded"] == 3
    assert isinstance(report["excluded_files"], list)
    assert isinstance(report["reason_counts"], dict)

    # Check that each excluded file has required fields
    for ef in report["excluded_files"]:
        assert "file" in ef
        assert "reason" in ef


def test_pipeline_idempotent(mini_corpus: Path, tmp_path: Path) -> None:
    """Running the pipeline twice should produce identical results."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    report1 = run_pipeline(mini_corpus, output_dir)
    report2 = run_pipeline(mini_corpus, output_dir)

    assert report1.kept == report2.kept
    assert report1.excluded == report2.excluded

    metadata1 = json.loads((output_dir / "metadata.json").read_text())
    metadata2 = json.loads((output_dir / "metadata.json").read_text())
    assert metadata1 == metadata2


def test_pipeline_cleaned_content_has_no_boilerplate(
    mini_corpus: Path, tmp_path: Path
) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    run_pipeline(mini_corpus, output_dir)

    cleaned = (output_dir / "cleaned" / "admissions.md").read_text()
    assert "Skip to Content" not in cleaned
    assert "Cal Poly Pomona]" not in cleaned
    assert "© 2024" not in cleaned
    assert "# Admissions" in cleaned
    assert "Requirements" in cleaned


def test_pipeline_empty_corpus(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "empty_corpus"
    corpus_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    report = run_pipeline(corpus_dir, output_dir)
    assert report.total_source_files == 0
    assert report.kept == 0
    assert report.excluded == 0
    assert (output_dir / "metadata.json").is_file()
    assert (output_dir / "filter_report.json").is_file()
    assert (output_dir / "freshness_manifest.json").is_file()
    assert (output_dir / "conflict_review.md").is_file()
