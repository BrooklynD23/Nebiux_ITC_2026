"""Tests for boilerplate stripping logic.

Uses inline fixtures — does NOT process the actual corpus.
"""

from __future__ import annotations

import pytest

from scripts.preprocess.strip_boilerplate import StrippedResult, strip_boilerplate


# ---------------------------------------------------------------------------
# Fixtures: realistic scraped page fragments
# ---------------------------------------------------------------------------

GOOD_CONTENT_PAGE = """\
[Skip to Main Content]

[Cal Poly Pomona]

Main Navigation

[Admissions](#) [Academics](#) [Campus Life](#)

# Computer Science Department

The Computer Science Department at Cal Poly Pomona offers undergraduate
and graduate programs that prepare students for careers in software
engineering, data science, and cybersecurity.

## Undergraduate Programs

- B.S. in Computer Science
- B.S. in Computer Information Systems

## Graduate Programs

- M.S. in Computer Science

| Program | Units | Duration |
|---------|-------|----------|
| B.S. CS | 180  | 4 years  |
| M.S. CS | 30   | 2 years  |

## Faculty

Our faculty members are active researchers in areas including:
artificial intelligence, machine learning, computer networks,
and software engineering.

---

Follow Us

[Facebook] [Twitter] [Instagram]

© 2024 California State Polytechnic University, Pomona
3801 West Temple Ave, Pomona, CA 91768
(909) 869-7659

Privacy Policy | Accessibility | Title IX
"""

NAV_ONLY_PAGE = """\
[Skip to Main Content]

[Cal Poly Pomona]

Toggle Menu

[Admissions](#)
[Academics](#)
[Campus Life](#)
[Research](#)
[About](#)

Main Navigation

© 2024 California State Polytechnic University, Pomona
"""

BREADCRUMB_PAGE = """\
Home > Admissions > Graduate Admissions

# Graduate Admissions

Welcome to CPP Graduate Admissions. We offer over 30 master's programs
across six colleges. Application deadlines vary by program.

## How to Apply

1. Submit your online application through Cal State Apply
2. Send official transcripts
3. Submit test scores if required
"""


class TestStripBoilerplate:
    """Test suite for strip_boilerplate function."""

    def test_preserves_headings(self) -> None:
        result = strip_boilerplate(GOOD_CONTENT_PAGE)
        assert "# Computer Science Department" in result.content
        assert "## Undergraduate Programs" in result.content
        assert "## Graduate Programs" in result.content
        assert "## Faculty" in result.content

    def test_preserves_paragraphs(self) -> None:
        result = strip_boilerplate(GOOD_CONTENT_PAGE)
        assert "software engineering, data science" in result.content

    def test_preserves_tables(self) -> None:
        result = strip_boilerplate(GOOD_CONTENT_PAGE)
        assert "| Program | Units | Duration |" in result.content
        assert "| B.S. CS | 180" in result.content

    def test_preserves_lists(self) -> None:
        result = strip_boilerplate(GOOD_CONTENT_PAGE)
        assert "- B.S. in Computer Science" in result.content
        assert "- M.S. in Computer Science" in result.content

    def test_removes_skip_to_content(self) -> None:
        result = strip_boilerplate(GOOD_CONTENT_PAGE)
        assert "Skip to Main Content" not in result.content

    def test_removes_nav_block(self) -> None:
        result = strip_boilerplate(GOOD_CONTENT_PAGE)
        assert "Main Navigation" not in result.content

    def test_removes_footer(self) -> None:
        result = strip_boilerplate(GOOD_CONTENT_PAGE)
        assert "© 2024" not in result.content
        assert "3801 West Temple" not in result.content
        assert "(909) 869-7659" not in result.content

    def test_removes_social_links(self) -> None:
        result = strip_boilerplate(GOOD_CONTENT_PAGE)
        assert "Follow Us" not in result.content
        assert "[Facebook]" not in result.content

    def test_removes_privacy_links(self) -> None:
        result = strip_boilerplate(GOOD_CONTENT_PAGE)
        assert "Privacy Policy" not in result.content
        assert "Accessibility" not in result.content

    def test_removes_breadcrumb(self) -> None:
        result = strip_boilerplate(BREADCRUMB_PAGE)
        assert "Home > Admissions > Graduate" not in result.content
        # But content after breadcrumb is preserved
        assert "# Graduate Admissions" in result.content

    def test_returns_stripped_result(self) -> None:
        result = strip_boilerplate(GOOD_CONTENT_PAGE)
        assert isinstance(result, StrippedResult)
        assert result.removed_sections > 0
        assert result.original_line_count > result.cleaned_line_count

    def test_nav_only_page_has_minimal_content(self) -> None:
        result = strip_boilerplate(NAV_ONLY_PAGE)
        # After stripping, very little should remain
        assert result.cleaned_line_count < 5

    def test_empty_input(self) -> None:
        result = strip_boilerplate("")
        assert result.content == ""
        assert result.cleaned_line_count == 0

    def test_plain_content_preserved(self) -> None:
        """Content without boilerplate should pass through unchanged."""
        content = "# Important Information\n\nThis is a test page with useful content."
        result = strip_boilerplate(content)
        assert "# Important Information" in result.content
        assert "useful content" in result.content

    def test_toggle_menu_removed(self) -> None:
        content = "Toggle Menu\n\n# Real Content\n\nSome text here."
        result = strip_boilerplate(content)
        assert "Toggle Menu" not in result.content
        assert "# Real Content" in result.content

    def test_cal_poly_pomona_nav_removed(self) -> None:
        content = "[Cal Poly Pomona]\n\n# Actual Page Title\n\nContent."
        result = strip_boilerplate(content)
        assert "[Cal Poly Pomona]" not in result.content
        assert "# Actual Page Title" in result.content

    def test_copyright_variations(self) -> None:
        content = "# Page\n\nContent here.\n\nCopyright © 2025 All Rights Reserved"
        result = strip_boilerplate(content)
        assert "Copyright" not in result.content
        assert "# Page" in result.content
