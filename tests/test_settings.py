"""Tests for environment/settings parsing."""

from __future__ import annotations

from pathlib import Path

from src.settings import Settings


def test_settings_parse_cors_origins_from_csv() -> None:
    settings = Settings(
        _env_file=None,
        CORS_ORIGINS="http://localhost:5173,https://demo.example",
    )

    assert settings.cors_origins == [
        "http://localhost:5173",
        "https://demo.example",
    ]


def test_settings_default_artifact_paths() -> None:
    settings = Settings(_env_file=None)

    assert settings.cleaned_dir == Path("data/cleaned")
    assert settings.metadata_path == Path("data/metadata.json")
    assert settings.chunk_manifest_path == Path("data/chunks.jsonl")
    assert settings.whoosh_dir == Path("data/indexes/whoosh")
