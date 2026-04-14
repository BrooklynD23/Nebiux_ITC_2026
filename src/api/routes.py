"""Chat route handler for POST /chat."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from src.audio_transcription import (
    SUPPORTED_AUDIO_CONTENT_TYPES,
    AudioTranscriber,
    AudioTranscriptionUnavailableError,
    AudioTranscriptionUpstreamError,
    OpenAIAudioTranscriber,
    normalize_audio_content_type,
)
from src.agent.tool_loop import run_tool_loop
from src.conversation import ConversationStore
from src.models import ChatRequest, ChatResponse, TranscriptionResponse
from src.settings import Settings, get_settings

logger = logging.getLogger(__name__)

router = APIRouter()


def get_conversation_store(request: Request) -> ConversationStore | None:
    """Return the app-scoped conversation store, if configured.

    Returns ``None`` when the store has not been attached to ``app.state``
    (for example in legacy tests that bypass the FastAPI lifespan).
    """
    return getattr(request.app.state, "conversation_store", None)


def get_retriever(request: Request) -> object | None:
    """Return the app-scoped retriever, if configured."""
    return getattr(request.app.state, "retriever", None)


def get_llm_runner(request: Request) -> object | None:
    """Return an injected tool-loop runner for tests, if configured."""
    return getattr(request.app.state, "llm_runner", None)


def get_audio_transcriber(request: Request) -> AudioTranscriber:
    """Return an injected transcriber for tests or the default provider."""
    injected = getattr(request.app.state, "audio_transcriber", None)
    if injected is not None:
        return injected
    return OpenAIAudioTranscriber()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    store: ConversationStore | None = Depends(get_conversation_store),
    retriever: object | None = Depends(get_retriever),
    llm_runner: object | None = Depends(get_llm_runner),
) -> ChatResponse:
    """Handle a user chat message and return a grounded answer."""
    try:
        response = await run_tool_loop(
            message=request.message,
            conversation_id=(
                str(request.conversation_id)
                if request.conversation_id is not None
                else None
            ),
            store=store,
            max_turns=get_settings().conversation_history_max_turns,
            retriever=retriever,
            llm_runner=llm_runner,
        )
        return response
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error in chat handler")
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred. Please try again later.",
        ) from None


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(
    audio: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    transcriber: AudioTranscriber = Depends(get_audio_transcriber),
) -> dict[str, str]:
    """Transcribe a short uploaded audio clip into plain text."""
    content_type = normalize_audio_content_type(audio.content_type)
    if content_type not in SUPPORTED_AUDIO_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=(
                "Unsupported audio format. Please upload mp3, mp4, m4a, wav, "
                "or webm audio."
            ),
        )

    audio_bytes = audio.file.read()
    if len(audio_bytes) == 0:
        raise HTTPException(
            status_code=400,
            detail="Voice transcription requires a non-empty audio upload.",
        )

    if len(audio_bytes) > settings.voice_transcription_max_bytes:
        raise HTTPException(
            status_code=413,
            detail="Audio upload is too large for voice transcription.",
        )

    try:
        transcript = await transcriber.transcribe(
            filename=audio.filename or "voice-input.webm",
            content_type=content_type,
            audio_bytes=audio_bytes,
        )
    except AudioTranscriptionUnavailableError:
        raise HTTPException(
            status_code=503,
            detail="Voice transcription is unavailable right now.",
        ) from None
    except AudioTranscriptionUpstreamError:
        raise HTTPException(
            status_code=503,
            detail=(
                "Voice transcription is temporarily unavailable. Please try "
                "typing your question instead."
            ),
        ) from None
    except RuntimeError as exc:
        detail = str(exc).lower()
        if "not configured" in detail:
            raise HTTPException(
                status_code=503,
                detail="Voice transcription is unavailable right now.",
            ) from None
        logger.exception("Unexpected runtime error in transcribe handler")
        raise HTTPException(
            status_code=503,
            detail=(
                "Voice transcription is temporarily unavailable. Please try "
                "typing your question instead."
            ),
        ) from None
    except Exception:
        logger.exception("Unexpected error in transcribe handler")
        raise HTTPException(
            status_code=503,
            detail=(
                "Voice transcription is temporarily unavailable. Please try "
                "typing your question instead."
            ),
        ) from None

    normalized_transcript = transcript.strip()
    if not normalized_transcript:
        raise HTTPException(
            status_code=400,
            detail="No speech was detected in the uploaded audio.",
        )

    return {"transcript": normalized_transcript}
