"""Extract metadata from cleaned corpus pages.

Produces per-page metadata including title, URL, word count, heading count,
table presence, and quality flags as defined in the sprint-0 contract.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class PageMetadata:
    """Metadata for a single cleaned page."""

    source_file: str
    cleaned_file: str
    title: str
    url: str
    word_count: int
    heading_count: int
    has_tables: bool
    quality_flags: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dictionary."""
        return {
            "source_file": self.source_file,
            "cleaned_file": self.cleaned_file,
            "title": self.title,
            "url": self.url,
            "word_count": self.word_count,
            "heading_count": self.heading_count,
            "has_tables": self.has_tables,
            "quality_flags": list(self.quality_flags),
        }


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
_TABLE_SEPARATOR_RE = re.compile(r"^\s*\|[\s\-:|]+\|\s*$", re.MULTILINE)
_LIST_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+", re.MULTILINE)
_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")

# Threshold for "long_form" quality flag
LONG_FORM_THRESHOLD = 500


def _extract_title(content: str) -> str:
    """Extract the page title from the first heading.

    Falls back to the first non-empty line if no heading is found.
    """
    match = _HEADING_RE.search(content)
    if match:
        return match.group(1).strip()

    # Fallback: first non-empty line
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped:
            # Truncate long first lines
            return stripped[:120]

    return "Untitled"


def _count_words(content: str) -> int:
    """Count words in content, stripping markdown syntax."""
    clean = _LINK_RE.sub(r"\1", content)
    clean = re.sub(r"[#*_`~>|]", "", clean)
    clean = re.sub(r"^-{3,}$", "", clean, flags=re.MULTILINE)
    return len(clean.split())


def _count_headings(content: str) -> int:
    """Count markdown headings in content."""
    return len(_HEADING_RE.findall(content))


def _has_tables(content: str) -> bool:
    """Check if content contains markdown tables."""
    return bool(_TABLE_SEPARATOR_RE.search(content))


def _has_lists(content: str) -> bool:
    """Check if content contains markdown lists."""
    return bool(_LIST_RE.search(content))


def _build_quality_flags(
    content: str,
    word_count: int,
    heading_count: int,
    has_tables: bool,
) -> tuple[str, ...]:
    """Build the quality flags tuple for a page."""
    flags: list[str] = []

    if heading_count > 0:
        flags.append("has_headings")
    if has_tables:
        flags.append("has_tables")
    if _has_lists(content):
        flags.append("has_lists")
    if word_count >= LONG_FORM_THRESHOLD:
        flags.append("long_form")

    return tuple(flags)


def extract_metadata(
    source_file: str,
    cleaned_content: str,
    url_map: dict[str, str],
) -> PageMetadata:
    """Extract metadata from a cleaned page.

    Parameters
    ----------
    source_file:
        Original filename from the raw corpus (e.g., ``"admissions_index.md"``).
    cleaned_content:
        The markdown content after boilerplate stripping.
    url_map:
        Mapping from URL to filename, loaded from ``index.json``.
        The function reverses this to find the URL for a given filename.

    Returns
    -------
    PageMetadata:
        Extracted metadata for the page.
    """
    title = _extract_title(cleaned_content)
    word_count = _count_words(cleaned_content)
    heading_count = _count_headings(cleaned_content)
    tables = _has_tables(cleaned_content)

    # Reverse lookup: find URL for this filename
    url = ""
    for page_url, filename in url_map.items():
        if filename == source_file:
            url = page_url
            break

    quality_flags = _build_quality_flags(
        cleaned_content, word_count, heading_count, tables
    )

    return PageMetadata(
        source_file=source_file,
        cleaned_file=source_file,  # same filename in data/cleaned/
        title=title,
        url=url,
        word_count=word_count,
        heading_count=heading_count,
        has_tables=tables,
        quality_flags=quality_flags,
    )
