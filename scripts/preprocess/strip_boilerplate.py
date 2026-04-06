"""Structure-based boilerplate removal for scraped CPP web pages.

Detects and removes common boilerplate patterns found in university website
scrapes: navigation blocks, footers, social media links, cookie banners,
breadcrumb trails, and skip-to-content links. Preserves headings, paragraphs,
tables, lists, and other meaningful content.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class StrippedResult:
    """Result of boilerplate stripping."""

    content: str
    removed_sections: int
    original_line_count: int
    cleaned_line_count: int


# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------

# Navigation patterns: lines that are part of nav menus
_NAV_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^\s*\[skip to (?:main )?content\]", re.IGNORECASE),
    re.compile(r"^\s*\[skip navigation\]", re.IGNORECASE),
    re.compile(r"^\s*toggle (?:menu|navigation)", re.IGNORECASE),
    re.compile(r"^\s*\[menu\]", re.IGNORECASE),
    re.compile(r"^\s*\[search\]\s*$", re.IGNORECASE),
    re.compile(r"^\s*\[cal poly pomona\]", re.IGNORECASE),
    re.compile(r"^\s*\[cpp\]", re.IGNORECASE),
    re.compile(r"^\s*main navigation", re.IGNORECASE),
    re.compile(r"^\s*primary navigation", re.IGNORECASE),
    re.compile(r"^\s*secondary navigation", re.IGNORECASE),
    re.compile(r"^\s*site navigation", re.IGNORECASE),
    re.compile(r"^\s*mobile navigation", re.IGNORECASE),
    re.compile(r"^\s*breadcrumb", re.IGNORECASE),
]

# Footer patterns: lines commonly found in page footers
_FOOTER_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^\s*\u00a9\s*\d{4}", re.IGNORECASE),  # copyright
    re.compile(r"^\s*copyright\s*\u00a9?\s*\d{4}", re.IGNORECASE),
    re.compile(r"^\s*all rights reserved", re.IGNORECASE),
    re.compile(r"^\s*california state polytechnic university", re.IGNORECASE),
    re.compile(r"^\s*3801 west temple", re.IGNORECASE),
    re.compile(r"^\s*pomona,?\s*ca\s*91768", re.IGNORECASE),
    re.compile(r"^\s*\(909\)\s*\d{3}[\-\s]\d{4}", re.IGNORECASE),
    re.compile(r"^\s*privacy\s*(?:policy)?", re.IGNORECASE),
    re.compile(r"^\s*accessibility", re.IGNORECASE),
    re.compile(r"^\s*title\s*ix", re.IGNORECASE),
    re.compile(r"^\s*annual\s*security\s*report", re.IGNORECASE),
    re.compile(r"^\s*consumer\s*information", re.IGNORECASE),
]

# Social media patterns
_SOCIAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"^\s*\[?\s*(?:facebook|twitter|instagram|linkedin|youtube|"
        r"tiktok|snapchat|x\.com|threads)\s*\]?",
        re.IGNORECASE,
    ),
    re.compile(r"^\s*follow us", re.IGNORECASE),
    re.compile(r"^\s*connect with us", re.IGNORECASE),
    re.compile(r"^\s*social media", re.IGNORECASE),
    re.compile(r"^\s*share\s*(?:this|page)?:?\s*$", re.IGNORECASE),
]

# Cookie / privacy banner patterns
_COOKIE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"this (?:site|website) uses cookies", re.IGNORECASE),
    re.compile(r"cookie\s*(?:policy|preferences|settings|consent)", re.IGNORECASE),
    re.compile(r"we use cookies", re.IGNORECASE),
    re.compile(r"accept\s*(?:all\s*)?cookies", re.IGNORECASE),
]

# Breadcrumb patterns
_BREADCRUMB_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^\s*(?:home|cpp\.edu)\s*[>/\u00bb]\s*", re.IGNORECASE),
    re.compile(r"^\s*(?:home|cpp\.edu)\s*$", re.IGNORECASE),
    # Lines that look like "Home > Admissions > Requirements"
    re.compile(
        r"^\s*\w[\w\s]*(?:\s*[>/\u00bb]\s*\w[\w\s]*){2,}\s*$",
        re.IGNORECASE,
    ),
]

# Login / authentication gate patterns
_LOGIN_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"please\s*(?:log\s*in|sign\s*in)", re.IGNORECASE),
    re.compile(r"you\s*(?:must|need to)\s*(?:log\s*in|sign\s*in)", re.IGNORECASE),
    re.compile(r"bronco\s*direct\s*login", re.IGNORECASE),
    re.compile(r"sso\s*login", re.IGNORECASE),
    re.compile(r"cas\s*login", re.IGNORECASE),
    re.compile(r"authentication\s*required", re.IGNORECASE),
]

# Redirect patterns
_REDIRECT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"you\s*(?:are|will)\s*(?:be\s*)?redirect", re.IGNORECASE),
    re.compile(r"page\s*(?:has\s*)?moved", re.IGNORECASE),
    re.compile(r"this page has been (?:moved|relocated)", re.IGNORECASE),
    re.compile(r"redirect(?:ing)?\s*(?:to|\.\.\.)", re.IGNORECASE),
    re.compile(r"^\s*moved permanently", re.IGNORECASE),
    re.compile(r"^\s*301\s*redirect", re.IGNORECASE),
    re.compile(r"click\s*here\s*if\s*(?:you\s*are\s*)?not\s*redirect", re.IGNORECASE),
]

ALL_BOILERPLATE_PATTERNS: list[re.Pattern[str]] = (
    _NAV_PATTERNS
    + _FOOTER_PATTERNS
    + _SOCIAL_PATTERNS
    + _COOKIE_PATTERNS
    + _BREADCRUMB_PATTERNS
)

# Block-level markers: if a line matches, the entire surrounding block
# (contiguous non-blank lines) is likely boilerplate
_BLOCK_MARKERS: list[re.Pattern[str]] = [
    re.compile(r"^\s*#{1,6}\s*(?:footer|navigation|nav|menu)\s*$", re.IGNORECASE),
    re.compile(r"^\s*---+\s*$"),  # horizontal rules often delimit boilerplate
]

# ---------------------------------------------------------------------------
# Repeated-link detection: blocks that are mostly markdown links
# ---------------------------------------------------------------------------

_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")


def _is_link_heavy_line(line: str) -> bool:
    """Return True if the line is predominantly a markdown link."""
    stripped = line.strip()
    if not stripped:
        return False
    match = _LINK_RE.search(stripped)
    if not match:
        return False
    # If the link text + brackets constitute most of the line
    link_text_len = len(match.group(0))
    return link_text_len / len(stripped) > 0.7


# ---------------------------------------------------------------------------
# Core stripping logic
# ---------------------------------------------------------------------------


def _matches_any(line: str, patterns: list[re.Pattern[str]]) -> bool:
    """Check if a line matches any pattern in the list."""
    return any(p.search(line) for p in patterns)


def _split_into_blocks(lines: list[str]) -> list[list[str]]:
    """Split lines into blocks separated by blank lines."""
    blocks: list[list[str]] = []
    current_block: list[str] = []

    for line in lines:
        if line.strip():
            current_block.append(line)
        else:
            if current_block:
                blocks.append(current_block)
                current_block = []

    if current_block:
        blocks.append(current_block)

    return blocks


def _is_boilerplate_block(block: list[str]) -> bool:
    """Determine if an entire block is boilerplate.

    A block is boilerplate if:
    - Most lines (>50%) match boilerplate patterns, OR
    - The block is a header-level marker for boilerplate sections, OR
    - The block is predominantly navigation links (>70% link-heavy lines)
    """
    if not block:
        return True

    boilerplate_count = sum(
        1 for line in block if _matches_any(line, ALL_BOILERPLATE_PATTERNS)
    )

    # If more than half the block is boilerplate patterns
    if boilerplate_count > len(block) * 0.5:
        return True

    # Check for block-level markers
    if any(_matches_any(line, _BLOCK_MARKERS) for line in block):
        # Short blocks with markers are likely boilerplate
        if len(block) <= 3:
            return True

    # Check for link-heavy blocks (nav menus rendered as link lists)
    link_heavy_count = sum(1 for line in block if _is_link_heavy_line(line))
    if len(block) >= 3 and link_heavy_count / len(block) > 0.7:
        return True

    return False


def _is_content_heading(line: str) -> bool:
    """Check if a line is a markdown heading with actual content."""
    stripped = line.strip()
    if not stripped.startswith("#"):
        return False
    # Remove heading markers
    heading_text = stripped.lstrip("#").strip()
    if not heading_text:
        return False
    # Don't count boilerplate headings
    boilerplate_headings = {
        "footer",
        "navigation",
        "nav",
        "menu",
        "social media",
        "connect with us",
        "follow us",
        "quick links",
        "useful links",
        "related links",
        "site map",
        "sitemap",
    }
    return heading_text.lower() not in boilerplate_headings


def strip_boilerplate(raw_content: str) -> StrippedResult:
    """Remove boilerplate from a scraped markdown page.

    Uses structure-based detection rather than fixed-line offsets.
    Analyzes blocks of content and removes those that match boilerplate
    patterns (navigation, footers, social links, cookie banners, etc.).

    Parameters
    ----------
    raw_content:
        The raw markdown content of a scraped page.

    Returns
    -------
    StrippedResult:
        The cleaned content and statistics about what was removed.
    """
    lines = raw_content.split("\n")
    original_line_count = len(lines)

    blocks = _split_into_blocks(lines)
    kept_blocks: list[list[str]] = []
    removed_count = 0

    for block in blocks:
        if _is_boilerplate_block(block):
            removed_count += 1
        else:
            # Even in kept blocks, strip individual boilerplate lines
            cleaned_block = [
                line
                for line in block
                if not _matches_any(line, ALL_BOILERPLATE_PATTERNS)
            ]
            if cleaned_block:
                kept_blocks.append(cleaned_block)
            else:
                removed_count += 1

    # Reassemble with blank lines between blocks
    cleaned_lines: list[str] = []
    for i, block in enumerate(kept_blocks):
        cleaned_lines.extend(block)
        if i < len(kept_blocks) - 1:
            cleaned_lines.append("")

    # Final cleanup: remove leading/trailing blank lines
    content = "\n".join(cleaned_lines).strip()

    return StrippedResult(
        content=content,
        removed_sections=removed_count,
        original_line_count=original_line_count,
        cleaned_line_count=len(content.split("\n")) if content else 0,
    )
