"""Tests for citation URL normalization."""

from __future__ import annotations

import pytest

from src.citations import normalize_url


class TestNormalizeUrl:
    """Validate URL canonicalization logic."""

    def test_http_to_https(self) -> None:
        assert normalize_url("http://www.cpp.edu/page") == (
            "https://www.cpp.edu/page"
        )

    def test_percent_encoded_tilde(self) -> None:
        assert normalize_url("https://www.cpp.edu/%7Efaculty/page") == (
            "https://www.cpp.edu/~faculty/page"
        )

    def test_percent_encoded_tilde_lowercase(self) -> None:
        assert normalize_url("https://www.cpp.edu/%7efaculty/page") == (
            "https://www.cpp.edu/~faculty/page"
        )

    def test_trailing_slash_stripped(self) -> None:
        assert normalize_url("https://www.cpp.edu/admissions/") == (
            "https://www.cpp.edu/admissions"
        )

    def test_root_slash_preserved(self) -> None:
        assert normalize_url("https://www.cpp.edu/") == (
            "https://www.cpp.edu/"
        )

    def test_host_lowercased(self) -> None:
        assert normalize_url("https://WWW.CPP.EDU/Page") == (
            "https://www.cpp.edu/Page"
        )

    def test_combined_normalization(self) -> None:
        raw = "http://WWW.CPP.EDU/%7Efaculty/page/"
        assert normalize_url(raw) == "https://www.cpp.edu/~faculty/page"

    def test_empty_string_passthrough(self) -> None:
        assert normalize_url("") == ""

    def test_whitespace_only_passthrough(self) -> None:
        assert normalize_url("   ") == "   "

    def test_query_params_preserved(self) -> None:
        url = "http://www.cpp.edu/search?q=admissions"
        result = normalize_url(url)
        assert "q=admissions" in result
        assert result.startswith("https://")

    def test_non_standard_port_preserved(self) -> None:
        url = "http://www.cpp.edu:8080/page/"
        result = normalize_url(url)
        assert ":8080" in result
        assert result == "https://www.cpp.edu:8080/page"
