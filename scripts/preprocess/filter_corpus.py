"""Corpus filtering: apply discard rules to cleaned pages.

Discard reasons (from sprint-0 contract):
- redirect: page is just a redirect
- login-gated: requires login/authentication
- too-short-after-cleaning: less than 50 words after boilerplate removal
- low-value-hub: only navigation links, no substantive content
- boilerplate-only: nothing left after stripping boilerplate
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DiscardReason(str, Enum):
    """Reasons a page may be excluded from the cleaned corpus."""

    REDIRECT = "redirect"
    LOGIN_GATED = "login-gated"
    TOO_SHORT = "too-short-after-cleaning"
    LOW_VALUE_HUB = "low-value-hub"
    BOILERPLATE_ONLY = "boilerplate-only"


@dataclass(frozen=True)
class FilterResult:
    """Result of filtering a single page."""

    keep: bool
    reason: Optional[DiscardReason] = None


# Minimum word count after cleaning to keep a page
MIN_WORD_COUNT = 50

# Minimum ratio of non-link content to keep a page (for hub detection)
MIN_CONTENT_RATIO = 0.3

# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------

_REDIRECT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"you\s*(?:are|will)\s*(?:be\s*)?redirect", re.IGNORECASE),
    re.compile(r"being redirected", re.IGNORECASE),
    re.compile(r"will redirect you to", re.IGNORECASE),
    re.compile(r"page\s*(?:has\s*)?moved", re.IGNORECASE),
    re.compile(r"has moved to", re.IGNORECASE),
    re.compile(r"this page has been (?:moved|relocated)", re.IGNORECASE),
    re.compile(r"redirect(?:ing)?\s*(?:to|\.\.\.)", re.IGNORECASE),
    re.compile(r"moved permanently", re.IGNORECASE),
    re.compile(r"301\s*redirect", re.IGNORECASE),
    re.compile(r"click\s*here\s*if\s*(?:you\s*are\s*)?not\s*redirect", re.IGNORECASE),
    re.compile(r"please visit\s+<https?://", re.IGNORECASE),
    re.compile(
        r"http-equiv\s*=\s*[\"']?refresh", re.IGNORECASE
    ),
]

_LOGIN_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"please\s*(?:log\s*in|sign\s*in)", re.IGNORECASE),
    re.compile(r"you\s*(?:must|need to)\s*(?:log\s*in|sign\s*in)", re.IGNORECASE),
    re.compile(r"bronco\s*direct\s*login", re.IGNORECASE),
    re.compile(r"sso\s*login", re.IGNORECASE),
    re.compile(r"cas\s*login", re.IGNORECASE),
    re.compile(r"cas\.cpp\.edu/cas/login", re.IGNORECASE),
    re.compile(r"authentication\s*required", re.IGNORECASE),
    re.compile(r"log\s*in\s*to\s*(?:continue|access|view)", re.IGNORECASE),
    re.compile(r"sign\s*in\s*to\s*(?:continue|access|view)", re.IGNORECASE),
    re.compile(r"login\s*required", re.IGNORECASE),
    re.compile(r"please\s+(?:log\s*in|sign\s*in)\s+to\s+continue", re.IGNORECASE),
]

_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")


def _word_count(text: str) -> int:
    """Count words in text, excluding markdown syntax."""
    # Remove markdown links but keep link text
    clean = _LINK_RE.sub(r"\1", text)
    # Remove decorative images
    clean = re.sub(r"!\[.*?\]\(.*?\)", "", clean)
    # Remove markdown formatting
    clean = re.sub(r"[#*_`~>|]", "", clean)
    # Remove horizontal rules
    clean = re.sub(r"^-{3,}$", "", clean, flags=re.MULTILINE)
    words = clean.split()
    return len(words)


def _is_redirect(raw_content: str) -> bool:
    """Check if the raw page content indicates a redirect."""
    for pattern in _REDIRECT_PATTERNS:
        if pattern.search(raw_content):
            return True
    return False


def _is_login_gated(raw_content: str, cleaned_content: str) -> bool:
    """Check if the page is login gated.

    If a login signal appears but the cleaned page still has substantial
    content, it likely has a public page with an incidental login link.
    """
    has_login_signal = any(pattern.search(raw_content) for pattern in _LOGIN_PATTERNS)
    if not has_login_signal:
        return False
    return _word_count(cleaned_content) < MIN_WORD_COUNT


def _is_low_value_hub(cleaned_content: str) -> bool:
    """Check if a cleaned page is a low-value hub (mostly links).

    A hub page is one where the majority of the content is just
    navigation links to other pages, with minimal substantive text.
    """
    lines = [line for line in cleaned_content.split("\n") if line.strip()]
    if not lines:
        return True

    link_lines = 0
    content_lines = 0
    heading_lines = 0
    for line in lines:
        stripped = line.strip()
        # Lines that are just a markdown link or start with bullet + link
        if _LINK_RE.search(stripped):
            link_text = _LINK_RE.sub("", stripped).strip()
            # If removing links leaves almost nothing, it's a link line
            if len(link_text) < 10:
                link_lines += 1
        elif stripped.startswith("#"):
            heading_lines += 1
        elif len(stripped) > 20:
            content_lines += 1

    total = link_lines + content_lines + heading_lines
    if total == 0:
        return True

    # If more than 70% of the relevant lines are link-heavy and there is
    # very little substantive text, it's a hub.
    if total > 0 and link_lines / total > 0.7 and content_lines < 3:
        return True

    return False


def filter_page(
    raw_content: str,
    cleaned_content: str,
) -> FilterResult:
    """Apply discard rules to a page and decide whether to keep it.

    Checks are applied in priority order:
    1. redirect (checked on raw content)
    2. login-gated (checked on raw content)
    3. boilerplate-only (cleaned content is empty)
    4. too-short-after-cleaning (< 50 words)
    5. low-value-hub (mostly links)

    Parameters
    ----------
    raw_content:
        The original raw markdown before boilerplate stripping.
    cleaned_content:
        The content after boilerplate stripping.

    Returns
    -------
    FilterResult:
        Whether to keep the page, and if not, the reason for exclusion.
    """
    # Check on raw content first (before cleaning)
    if _is_redirect(raw_content):
        return FilterResult(keep=False, reason=DiscardReason.REDIRECT)

    if _is_login_gated(raw_content, cleaned_content):
        return FilterResult(keep=False, reason=DiscardReason.LOGIN_GATED)

    # Check cleaned content
    stripped = cleaned_content.strip()

    if not stripped:
        return FilterResult(keep=False, reason=DiscardReason.BOILERPLATE_ONLY)

    if _is_low_value_hub(stripped):
        return FilterResult(keep=False, reason=DiscardReason.LOW_VALUE_HUB)

    wc = _word_count(stripped)
    if wc < MIN_WORD_COUNT:
        return FilterResult(keep=False, reason=DiscardReason.TOO_SHORT)

    return FilterResult(keep=True)
