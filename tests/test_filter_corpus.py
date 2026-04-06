"""Tests for corpus filtering logic.

Uses inline fixtures — does NOT process the actual corpus.
"""

from __future__ import annotations

import pytest

from scripts.preprocess.filter_corpus import DiscardReason, FilterResult, filter_page


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

GOOD_RAW_CONTENT = """\
[Skip to Content]

# Cal Poly Pomona Admissions

The Office of Admissions at Cal Poly Pomona welcomes applications from
first-time freshmen, transfer students, and international students.
Our admissions process is designed to be straightforward and supportive.

## First-Time Freshmen

To be eligible for admission as a first-time freshman, applicants must
complete the following A-G requirements with a minimum GPA of 2.0.
SAT and ACT scores are not required for admission but may be used for
placement purposes.

## Transfer Students

Transfer students must have completed at least 60 semester units of
transferable coursework with a minimum GPA of 2.0. Priority is given
to students who have completed the Golden Four requirements.

## Important Dates

| Deadline | Date |
|----------|------|
| Fall application | October 1 - December 15 |
| Spring application | August 1 - August 31 |
"""

REDIRECT_RAW = """\
You are being redirected to the new page location.

Click here if you are not redirected automatically.
"""

LOGIN_GATED_RAW = """\
[Skip to Content]

# BroncoDirect

Please log in to access your student portal.

SSO Login required.
"""

SHORT_CLEANED = "This page has only a few words."

EMPTY_CLEANED = ""

HUB_PAGE_CLEANED = """\
# Quick Links

[Admissions](https://www.cpp.edu/admissions)
[Financial Aid](https://www.cpp.edu/financial-aid)
[Housing](https://www.cpp.edu/housing)
[Dining](https://www.cpp.edu/dining)
[Library](https://www.cpp.edu/library)
[Athletics](https://www.cpp.edu/athletics)
[Career Center](https://www.cpp.edu/career)
[Student Health](https://www.cpp.edu/health)
[IT Services](https://www.cpp.edu/it)
[Parking](https://www.cpp.edu/parking)
"""


class TestFilterPage:
    """Test suite for filter_page function."""

    def test_good_page_kept(self) -> None:
        result = filter_page(GOOD_RAW_CONTENT, GOOD_RAW_CONTENT)
        assert result.keep is True
        assert result.reason is None

    def test_redirect_detected(self) -> None:
        result = filter_page(REDIRECT_RAW, "")
        assert result.keep is False
        assert result.reason == DiscardReason.REDIRECT

    def test_redirect_page_moved(self) -> None:
        raw = "This page has moved to a new location."
        result = filter_page(raw, "")
        assert result.keep is False
        assert result.reason == DiscardReason.REDIRECT

    def test_redirect_301(self) -> None:
        raw = "301 redirect\n\nMoved permanently."
        result = filter_page(raw, "")
        assert result.keep is False
        assert result.reason == DiscardReason.REDIRECT

    def test_login_gated_detected(self) -> None:
        result = filter_page(LOGIN_GATED_RAW, "")
        assert result.keep is False
        assert result.reason == DiscardReason.LOGIN_GATED

    def test_login_gated_sso(self) -> None:
        raw = "You must sign in to continue. SSO Login"
        result = filter_page(raw, "")
        assert result.keep is False
        assert result.reason == DiscardReason.LOGIN_GATED

    def test_login_gated_authentication_required(self) -> None:
        raw = "Authentication required to view this page."
        result = filter_page(raw, "")
        assert result.keep is False
        assert result.reason == DiscardReason.LOGIN_GATED

    def test_boilerplate_only(self) -> None:
        result = filter_page("some raw content", EMPTY_CLEANED)
        assert result.keep is False
        assert result.reason == DiscardReason.BOILERPLATE_ONLY

    def test_too_short_after_cleaning(self) -> None:
        result = filter_page("raw content", SHORT_CLEANED)
        assert result.keep is False
        assert result.reason == DiscardReason.TOO_SHORT

    def test_exactly_50_words_kept(self) -> None:
        words = " ".join(f"word{i}" for i in range(50))
        result = filter_page("raw", words)
        assert result.keep is True

    def test_49_words_excluded(self) -> None:
        words = " ".join(f"word{i}" for i in range(49))
        result = filter_page("raw", words)
        assert result.keep is False
        assert result.reason == DiscardReason.TOO_SHORT

    def test_low_value_hub_detected(self) -> None:
        result = filter_page("raw content", HUB_PAGE_CLEANED)
        assert result.keep is False
        assert result.reason == DiscardReason.LOW_VALUE_HUB

    def test_page_with_links_and_content_kept(self) -> None:
        """Pages with links AND substantive text should be kept."""
        content = """\
# Financial Aid Resources

Financial aid at Cal Poly Pomona helps students pay for their education
through grants, scholarships, loans, and work-study programs. The office
serves over 20,000 students each year with various forms of assistance.

## Useful Links

[FAFSA](https://fafsa.ed.gov) - Federal student aid application
[Cal Grant](https://www.csac.ca.gov) - California state grants
[CPP Scholarships](https://www.cpp.edu/scholarships) - University scholarships

## Contact

Visit us in Building 98, Room 1-21, or call (909) 869-3700.
"""
        result = filter_page("raw", content)
        assert result.keep is True

    def test_filter_priority_redirect_before_login(self) -> None:
        """Redirect check should happen before login check."""
        raw = "You are being redirected. Please log in."
        result = filter_page(raw, "")
        assert result.reason == DiscardReason.REDIRECT

    def test_filter_priority_login_before_boilerplate(self) -> None:
        """Login check should happen before boilerplate check."""
        raw = "Please log in to continue."
        result = filter_page(raw, "")
        assert result.reason == DiscardReason.LOGIN_GATED

    def test_filter_result_is_frozen(self) -> None:
        result = filter_page("raw", "enough words " * 50)
        assert isinstance(result, FilterResult)
