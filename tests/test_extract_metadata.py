"""Tests for metadata extraction logic."""

from __future__ import annotations

import pytest

from scripts.preprocess.extract_metadata import PageMetadata, extract_metadata


SAMPLE_CONTENT = """\
# Computer Science Department

The CS department offers programs in software engineering and data science.

## Programs

- B.S. in Computer Science
- M.S. in Computer Science

## Tuition

| Program | Cost |
|---------|------|
| B.S.    | $7k  |
| M.S.    | $9k  |

Additional information about financial aid is available. Students should
consult the financial aid office for details about grants, scholarships,
and loan programs. The department also offers teaching assistantships
for qualified graduate students.
"""

SAMPLE_URL_MAP = {
    "https://www.cpp.edu/cs/index.shtml": "cs_index.md",
    "https://www.cpp.edu/admissions/index.shtml": "admissions_index.md",
}


class TestExtractMetadata:
    def test_extracts_title_from_heading(self) -> None:
        meta = extract_metadata("cs_index.md", SAMPLE_CONTENT, SAMPLE_URL_MAP)
        assert meta.title == "Computer Science Department"

    def test_extracts_url_from_map(self) -> None:
        meta = extract_metadata("cs_index.md", SAMPLE_CONTENT, SAMPLE_URL_MAP)
        assert meta.url == "https://www.cpp.edu/cs/index.shtml"

    def test_empty_url_when_not_in_map(self) -> None:
        meta = extract_metadata("unknown.md", SAMPLE_CONTENT, SAMPLE_URL_MAP)
        assert meta.url == ""

    def test_word_count_positive(self) -> None:
        meta = extract_metadata("cs_index.md", SAMPLE_CONTENT, SAMPLE_URL_MAP)
        assert meta.word_count > 20

    def test_heading_count(self) -> None:
        meta = extract_metadata("cs_index.md", SAMPLE_CONTENT, SAMPLE_URL_MAP)
        assert meta.heading_count == 3  # h1 + 2 h2

    def test_has_tables(self) -> None:
        meta = extract_metadata("cs_index.md", SAMPLE_CONTENT, SAMPLE_URL_MAP)
        assert meta.has_tables is True

    def test_no_tables(self) -> None:
        content = "# Title\n\nJust some text without tables."
        meta = extract_metadata("test.md", content, {})
        assert meta.has_tables is False

    def test_quality_flags_headings(self) -> None:
        meta = extract_metadata("cs_index.md", SAMPLE_CONTENT, SAMPLE_URL_MAP)
        assert "has_headings" in meta.quality_flags

    def test_quality_flags_tables(self) -> None:
        meta = extract_metadata("cs_index.md", SAMPLE_CONTENT, SAMPLE_URL_MAP)
        assert "has_tables" in meta.quality_flags

    def test_quality_flags_lists(self) -> None:
        meta = extract_metadata("cs_index.md", SAMPLE_CONTENT, SAMPLE_URL_MAP)
        assert "has_lists" in meta.quality_flags

    def test_quality_flags_long_form(self) -> None:
        long_content = "# Title\n\n" + "word " * 600
        meta = extract_metadata("long.md", long_content, {})
        assert "long_form" in meta.quality_flags

    def test_source_file_matches(self) -> None:
        meta = extract_metadata("cs_index.md", SAMPLE_CONTENT, SAMPLE_URL_MAP)
        assert meta.source_file == "cs_index.md"
        assert meta.cleaned_file == "cs_index.md"

    def test_to_dict(self) -> None:
        meta = extract_metadata("cs_index.md", SAMPLE_CONTENT, SAMPLE_URL_MAP)
        d = meta.to_dict()
        assert isinstance(d, dict)
        assert d["source_file"] == "cs_index.md"
        assert isinstance(d["quality_flags"], list)

    def test_title_fallback_no_heading(self) -> None:
        content = "Just a plain page with no headings at all."
        meta = extract_metadata("plain.md", content, {})
        assert meta.title == "Just a plain page with no headings at all."

    def test_frozen_dataclass(self) -> None:
        meta = extract_metadata("cs_index.md", SAMPLE_CONTENT, SAMPLE_URL_MAP)
        with pytest.raises(AttributeError):
            meta.title = "modified"  # type: ignore[misc]
