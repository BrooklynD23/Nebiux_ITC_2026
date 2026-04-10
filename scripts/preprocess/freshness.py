"""Freshness scoring for preprocessed corpus documents.

Ported from preprocessing_pipeline_test/scripts/corpus_freshness.py.
Computes per-document outdated risk scores based on URL patterns,
content signals, and cluster context.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from scripts.preprocess.filter_corpus import FilterResult

GENERIC_PATH_SEGMENTS = {
    "www",
    "index",
    "index1",
    "index2",
    "home",
    "default",
    "authenticated",
}

LEGACY_URL_TOKENS = {
    "old",
    "archive",
    "archived",
    "legacy",
    "deprecated",
    "previous",
    "index1",
    "index2",
    "mobile",
}

STALE_PHRASES = (
    "old site",
    "older version",
    "no longer updated",
    "archived page",
    "deprecated",
    "superseded",
    "this page has moved",
)

REDIRECT_HINTS = (
    "redirect",
    "redirected",
    "moved to",
    "moved permanently",
    "please visit",
)

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?:\+?1[\s.-]?)?(?:\(?(\d{3})\)?[\s.-]?(\d{3})[\s.-]?(\d{4}))")
MONEY_RE = re.compile(r"\$\s?\d[\d,]*(?:\.\d{2})?")
YEAR_RE = re.compile(r"\b(20\d{2})\b")
DATE_RE = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{1,2}(?:,\s+|\s+)(20\d{2})\b",
    re.IGNORECASE,
)
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", re.MULTILINE)
WORD_RE = re.compile(r"[a-z0-9]+")
LINK_ONLY_RE = re.compile(r"^\[([^\]]+)\]\([^)]+\)$")
INLINE_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
GENERIC_TITLE_VALUES = {"cpp news", "news"}


def _unique_sorted(values: list[str]) -> list[str]:
    return sorted({value for value in values if value})


def _normalize_slug(value: str) -> str:
    words = WORD_RE.findall(value.lower())
    return "-".join(words[:8]) if words else "untitled"


def _clean_title_candidate(value: str) -> str:
    candidate = value.strip(" -*\t")
    link_match = LINK_ONLY_RE.match(candidate)
    if link_match:
        candidate = link_match.group(1)
    candidate = INLINE_LINK_RE.sub(r"\1", candidate)
    candidate = " ".join(candidate.split())
    if candidate.lower() in GENERIC_TITLE_VALUES:
        return ""
    return candidate


def _extract_title(text: str) -> str:
    for match in HEADING_RE.finditer(text):
        title = _clean_title_candidate(match.group(1))
        if title:
            return title

    for raw_line in text.splitlines():
        line = _clean_title_candidate(raw_line)
        if not line:
            continue
        if line.lower() == "search":
            continue
        return line[:160]
    return "Untitled"


def _extract_path_tokens(source_url: str) -> list[str]:
    parsed = urlparse(source_url)
    tokens: list[str] = []
    for segment in parsed.path.split("/"):
        part = segment.strip().lower()
        if not part:
            continue
        part = re.sub(r"\.(s?html?|md)$", "", part)
        if part in GENERIC_PATH_SEGMENTS:
            continue
        tokens.extend(
            token
            for token in re.split(r"[-_]+", part)
            if token and len(token) > 1 and not token.isdigit()
        )
    return tokens


def build_topic_key(source_url: str, title: str) -> str:
    """Build a canonical topic key from URL path and document title."""
    raw_tokens = _extract_path_tokens(source_url)
    path_tokens = [t for t in raw_tokens if t not in LEGACY_URL_TOKENS]
    path_root = "-".join(path_tokens[:4]) if path_tokens else "root"
    title_clean = _clean_title_candidate(title)
    if not title_clean:
        return path_root
    title_slug = _normalize_slug(title_clean)
    return f"{path_root}__{title_slug}"


def _extract_years(text: str) -> list[int]:
    max_reasonable_year = datetime.now(timezone.utc).year + 1
    years = [int(match.group(1)) for match in YEAR_RE.finditer(text)]
    years.extend(int(match.group(1)) for match in DATE_RE.finditer(text))
    years = [year for year in years if 2000 <= year <= max_reasonable_year]
    return sorted(set(years))


def _extract_emails(text: str) -> list[str]:
    return _unique_sorted([match.group(0).lower() for match in EMAIL_RE.finditer(text)])


def _extract_phones(text: str) -> list[str]:
    phones = []
    for area, prefix, suffix in PHONE_RE.findall(text):
        phones.append(f"{area}{prefix}{suffix}")
    return _unique_sorted(phones)


def _extract_dates(text: str) -> list[str]:
    return _unique_sorted([match.group(0) for match in DATE_RE.finditer(text)])


def _extract_money(text: str) -> list[str]:
    return _unique_sorted(
        [match.group(0).replace(" ", "") for match in MONEY_RE.finditer(text)]
    )


def _find_phrase_hits(text: str, phrases: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    return [phrase for phrase in phrases if phrase in lowered]


def collect_document_metadata(
    *,
    filename: str,
    source_url: str,
    cleaned_body: str,
    filter_result: FilterResult,
    alias_count: int,
    file_mtime_iso: str,
) -> dict[str, Any]:
    """Collect per-document metadata for freshness scoring.

    Parameters
    ----------
    filename:
        The source filename (relative to the corpus root).
    source_url:
        The primary URL the file was fetched from.
    cleaned_body:
        The content after boilerplate stripping.
    filter_result:
        The result of filter_page(), providing keep/category/duplicate info.
    alias_count:
        Number of URLs that map to this file (from the reverse URL map).
    file_mtime_iso:
        ISO-format modification time of the source file.

    Returns
    -------
    dict:
        Metadata record suitable for freshness scoring and conflict detection.
    """
    title = _extract_title(cleaned_body)
    years = _extract_years(cleaned_body)
    path_tokens = _extract_path_tokens(source_url)
    legacy_url_hits = [token for token in path_tokens if token in LEGACY_URL_TOKENS]
    stale_phrase_hits = _find_phrase_hits(cleaned_body, STALE_PHRASES)
    redirect_hint_hits = _find_phrase_hits(cleaned_body, REDIRECT_HINTS)

    return {
        "filename": filename,
        "source_url": source_url,
        "title": title,
        "topic_key": build_topic_key(source_url, title),
        "body_len": len(cleaned_body),
        "heading_count": len(HEADING_RE.findall(cleaned_body)),
        "latest_year": max(years) if years else None,
        "all_years": years,
        "date_mentions": _extract_dates(cleaned_body),
        "contact_emails": _extract_emails(cleaned_body),
        "contact_phones": _extract_phones(cleaned_body),
        "money_amounts": _extract_money(cleaned_body),
        "stale_phrase_hits": stale_phrase_hits,
        "legacy_url_hits": legacy_url_hits,
        "redirect_hint_hits": redirect_hint_hits,
        "file_mtime_iso": file_mtime_iso,
        "category": filter_result.category,
        "is_duplicate": filter_result.is_duplicate,
        "duplicate_group_size": filter_result.duplicate_group_size,
        "alias_count": alias_count,
        "keep": filter_result.keep,
    }


def compute_outdated_risk(
    metadata: dict[str, Any],
    *,
    cluster_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute an outdated-risk score for a document.

    Parameters
    ----------
    metadata:
        The metadata record from collect_document_metadata().
    cluster_context:
        Optional dict with keys:
        - ``max_latest_year``: the most recent year seen in the topic cluster
        - ``current_year``: the reference year for staleness (defaults to now)
        - ``cluster_has_conflicts``: whether the cluster has conflicting data

    Returns
    -------
    dict:
        {outdated_risk_score, outdated_risk_level, risk_reasons, newer_candidate_year}
    """
    cluster_context = cluster_context or {}
    score = 0
    reasons: list[str] = []

    if metadata.get("legacy_url_hits"):
        score += 3
        reasons.append("legacy_url")

    if metadata.get("stale_phrase_hits"):
        score += 3
        reasons.append("stale_language")

    if metadata.get("redirect_hint_hits"):
        score += 2
        reasons.append("redirect_language")

    if metadata.get("body_len", 0) < 500:
        score += 1
        reasons.append("thin_content")

    if metadata.get("duplicate_group_size", 1) > 1:
        score += 1
        reasons.append("duplicate_group")

    latest_year = metadata.get("latest_year")
    max_latest_year = cluster_context.get("max_latest_year")
    if latest_year and max_latest_year and latest_year < max_latest_year:
        gap = max_latest_year - latest_year
        score += 3 if gap >= 2 else 2
        reasons.append("older_than_cluster_peer")

    current_year = cluster_context.get("current_year")
    if latest_year and current_year and latest_year <= current_year - 3:
        score += 1
        reasons.append("old_explicit_year")

    if cluster_context.get("cluster_has_conflicts"):
        score += 2
        reasons.append("conflicting_cluster")

    if score >= 8:
        level = "high"
    elif score >= 4:
        level = "medium"
    else:
        level = "low"

    return {
        "outdated_risk_score": score,
        "outdated_risk_level": level,
        "risk_reasons": reasons,
        "newer_candidate_year": max_latest_year,
    }
