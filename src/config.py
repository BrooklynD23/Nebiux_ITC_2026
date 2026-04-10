"""Application configuration and LLM client factory."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from src.settings import get_settings

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM back-ends."""

    GEMINI = "gemini"
    OPENAI = "openai"


def _resolve_provider() -> LLMProvider:
    """Read LLM_PROVIDER from the settings (default: gemini)."""
    raw = get_settings().llm_provider.strip().lower()
    try:
        return LLMProvider(raw)
    except ValueError as exc:
        raise ValueError(
            f"LLM_PROVIDER must be 'gemini' or 'openai', got '{raw}'"
        ) from exc


def _require_value(name: str, value: str | None) -> str:
    """Return a setting value or raise with a helpful message."""
    cleaned = (value or "").strip()
    if not cleaned:
        raise EnvironmentError(
            f"Environment variable {name} is required but not set. "
            f"Copy .env.example to .env and fill it in."
        )
    return cleaned


def _resolve_provider_key(provider: LLMProvider) -> str:
    """Read the matching provider key from settings."""
    settings = get_settings()

    if provider is LLMProvider.GEMINI:
        return _require_value("GEMINI_API_KEY", settings.gemini_api_key)

    return _require_value("OPENAI_API_KEY", settings.openai_api_key)


def get_llm_client() -> Any:
    """Return the configured LLM client instance.

    Raises
    ------
    EnvironmentError
        If the required API key is missing.
    ValueError
        If LLM_PROVIDER has an invalid value.
    """
    provider = _resolve_provider()
    api_key = _resolve_provider_key(provider)

    if provider is LLMProvider.GEMINI:
        from google import genai  # type: ignore[import-untyped]

        client = genai.Client(api_key=api_key)
        logger.info("Initialized Gemini client")
        return client

    # provider is LLMProvider.OPENAI
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    logger.info("Initialized OpenAI client")
    return client


def get_provider() -> LLMProvider:
    """Return the active LLM provider enum without creating a client."""
    return _resolve_provider()
