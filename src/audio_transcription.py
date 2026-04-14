"""Helpers for short-form audio transcription."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from io import BytesIO
from typing import Protocol

from src.settings import Settings, get_settings

logger = logging.getLogger(__name__)

SUPPORTED_AUDIO_CONTENT_TYPES = frozenset(
    {
        "audio/m4a",
        "audio/mp3",
        "audio/mp4",
        "audio/mpga",
        "audio/mpeg",
        "audio/wav",
        "audio/webm",
        "audio/x-wav",
    }
)


class AudioTranscriptionUnavailableError(RuntimeError):
    """Raised when transcription is disabled or not configured."""


class AudioTranscriptionUpstreamError(RuntimeError):
    """Raised when the upstream transcription provider fails."""


class AudioTranscriber(Protocol):
    """Interface for audio transcription providers."""

    async def transcribe(
        self,
        *,
        filename: str,
        content_type: str,
        audio_bytes: bytes,
    ) -> str:
        """Transcribe a short audio clip into plain text."""


@dataclass(slots=True)
class OpenAIAudioTranscriber:
    """OpenAI-backed implementation for short audio transcription."""

    settings: Settings | None = None

    async def transcribe(
        self,
        *,
        filename: str,
        content_type: str,
        audio_bytes: bytes,
    ) -> str:
        settings = self.settings or get_settings()
        if not settings.voice_transcription_enabled:
            raise AudioTranscriptionUnavailableError(
                "Voice transcription is disabled."
            )
        if not (settings.openai_api_key or "").strip():
            raise AudioTranscriptionUnavailableError(
                "Voice transcription is unavailable because OpenAI is not configured."
            )

        return await asyncio.to_thread(
            self._transcribe_sync,
            settings,
            filename,
            content_type,
            audio_bytes,
        )

    def _transcribe_sync(
        self,
        settings: Settings,
        filename: str,
        content_type: str,
        audio_bytes: bytes,
    ) -> str:
        file_obj = BytesIO(audio_bytes)
        file_obj.name = filename

        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key)
            response = client.audio.transcriptions.create(
                model=settings.voice_transcription_model,
                file=(filename, file_obj, content_type),
                response_format="text",
            )
        except Exception as exc:  # pragma: no cover - network/provider boundary
            logger.exception("OpenAI transcription failed")
            raise AudioTranscriptionUpstreamError(
                "Voice transcription failed upstream."
            ) from exc

        transcript = getattr(response, "text", response)
        return str(transcript)


def normalize_audio_content_type(content_type: str | None) -> str:
    """Collapse content type parameters into a normalized media type."""

    cleaned = (content_type or "").strip().lower()
    if ";" in cleaned:
        cleaned = cleaned.split(";", 1)[0].strip()
    return cleaned
