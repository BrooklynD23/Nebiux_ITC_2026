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


def test_settings_builds_grounding_config() -> None:
    settings = Settings(
        _env_file=None,
        GROUNDING_MIN_TOP_SCORE=0.4,
        GROUNDING_MIN_RESULTS=2,
        GROUNDING_SCORE_AGGREGATION="mean_top3",
        GROUNDING_EXPECTED_TOP_K=7,
    )

    config = settings.grounding_config
    assert config.min_top_score == 0.4
    assert config.min_results == 2
    assert config.score_aggregation == "mean_top3"
    assert config.expected_top_k == 7


def test_settings_parse_admin_token_and_log_level() -> None:
    settings = Settings(
        _env_file=None,
        ADMIN_API_TOKEN="pilot-secret",
        LOG_LEVEL="DEBUG",
    )

    assert settings.admin_api_token == "pilot-secret"
    assert settings.log_level == "DEBUG"


def test_settings_parse_retriever_mode() -> None:
    settings = Settings(_env_file=None, RETRIEVER_MODE="bm25")

    assert settings.retriever_mode == "bm25"


def test_settings_default_voice_transcription_values() -> None:
    settings = Settings(_env_file=None)

    assert settings.voice_transcription_enabled is True
    assert settings.voice_transcription_model == "gpt-4o-mini-transcribe"
    assert settings.voice_transcription_max_bytes == 5_000_000
