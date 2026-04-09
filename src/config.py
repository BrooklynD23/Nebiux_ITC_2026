"""Application configuration and LLM client factory.

All LLM access goes through ``get_llm_client()`` so callers never
import provider SDKs directly.
"""

from __future__ import annotations

import logging
import os
from enum import Enum
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM back-ends."""

    GEMINI = "gemini"
    OPENAI = "openai"


def _resolve_provider() -> LLMProvider:
    """Read LLM_PROVIDER from the environment (default: gemini)."""
    raw = os.environ.get("LLM_PROVIDER", "gemini").strip().lower()
    try:
        return LLMProvider(raw)
    except ValueError as exc:
        raise ValueError(
            f"LLM_PROVIDER must be 'gemini' or 'openai', got '{raw}'"
        ) from exc


def _require_env(name: str) -> str:
    """Return an env var or raise with a helpful message."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise EnvironmentError(
            f"Environment variable {name} is required but not set. "
            f"Copy .env.example to .env and fill it in."
        )
    return value


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

    if provider is LLMProvider.GEMINI:
        api_key = _require_env("GEMINI_API_KEY")
        from google import genai  # type: ignore[import-untyped]

        client = genai.Client(api_key=api_key)
        logger.info("Initialized Gemini client")
        return client

    # provider is LLMProvider.OPENAI
    api_key = _require_env("OPENAI_API_KEY")
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    logger.info("Initialized OpenAI client")
    return client


def get_provider() -> LLMProvider:
    """Return the active LLM provider enum without creating a client."""
    return _resolve_provider()
