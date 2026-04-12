"""Query cleanup helpers for retrieval-oriented normalization."""

from __future__ import annotations

from dataclasses import dataclass
import re

from src.agent.abbreviations import ABBREVIATION_MAP

_LEADING_FILLER_PHRASES = (
    "i would like to know",
    "could you tell me",
    "please tell me",
    "can you tell me",
    "i want to know",
)
_LEADING_FILLER_RE = re.compile(
    r"^(?:"
    + "|".join(re.escape(phrase) for phrase in _LEADING_FILLER_PHRASES)
    + r")\b[\s,:;.-]*"
)
_REPEATED_PUNCTUATION_RE = re.compile(r"([?!.,])\1+")
_BOUNDARY_STRIP_RE = re.compile(r"(?<!\w)[?!\"']+|[?!\"']+(?!\w)")
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class NormalizedQuery:
    """Represents the raw and normalized forms of a user query."""

    original: str
    normalized_text: str
    is_ambiguous: bool


def _strip_filler_phrases(text: str) -> str:
    return _LEADING_FILLER_RE.sub("", text, count=1)


def _normalize_punctuation(text: str) -> str:
    text = _REPEATED_PUNCTUATION_RE.sub(r"\1", text)
    text = _BOUNDARY_STRIP_RE.sub("", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def _expand_abbreviations(tokens: list[str]) -> str:
    return " ".join(ABBREVIATION_MAP.get(token, token) for token in tokens)


def normalize(raw: str) -> NormalizedQuery:
    """Normalize a raw query for retrieval while preserving the original."""

    text = raw.strip().lower()
    text = _strip_filler_phrases(text)
    text = _normalize_punctuation(text)

    tokens = text.split()
    is_ambiguous = len(tokens) < 3
    normalized_text = _expand_abbreviations(tokens)

    return NormalizedQuery(
        original=raw,
        normalized_text=normalized_text,
        is_ambiguous=is_ambiguous,
    )
