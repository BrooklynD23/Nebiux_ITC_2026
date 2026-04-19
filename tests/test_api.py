"""Tests for the FastAPI chat and health handlers."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import uuid

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from starlette.datastructures import Headers, UploadFile

from src.api import main as main_module
from src.api.routes import chat, transcribe
from src.models import ChatRequest
from src.retrieval.chroma_index import ChromaCollectionMissingError
from src.settings import Settings
from tests.fakes import FakeRetriever, fake_llm_runner


class TestHealthEndpoint:
    """Verify the liveness probe."""

    @pytest.mark.asyncio
    async def test_health_returns_ok(self) -> None:
        data = await main_module.health()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_reports_missing_chroma_collection(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(main_module, "chroma_collection_exists", lambda _: False)

        data = await main_module.health()

        assert data["artifacts"]["chroma_ready"] is False


def test_build_retriever_falls_back_to_bm25_when_chroma_collection_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from src.retrieval import hybrid_retriever, whoosh_retriever

    class BrokenHybridRetriever:
        def __init__(self) -> None:
            raise ChromaCollectionMissingError(Path("data/indexes/chroma"))

    class FakeWhooshRetriever:
        pass

    monkeypatch.setattr(hybrid_retriever, "HybridRetriever", BrokenHybridRetriever)
    monkeypatch.setattr(whoosh_retriever, "WhooshRetriever", FakeWhooshRetriever)

    with caplog.at_level("INFO"):
        retriever, mode = main_module._build_retriever()

    assert isinstance(retriever, FakeWhooshRetriever)
    assert mode == "bm25"
    assert "falling back to bm25-only mode" in caplog.text.lower()
    assert "traceback" not in caplog.text.lower()


def test_build_retriever_respects_explicit_bm25_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.retrieval import whoosh_retriever

    class FakeWhooshRetriever:
        pass

    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: type("SettingsStub", (), {"retriever_mode": "bm25"})(),
    )
    monkeypatch.setattr(whoosh_retriever, "WhooshRetriever", FakeWhooshRetriever)

    retriever, mode = main_module._build_retriever()

    assert isinstance(retriever, FakeWhooshRetriever)
    assert mode == "bm25"


class TestChatEndpoint:
    """Verify the chat handler returns valid contract shapes."""

    @pytest.mark.asyncio
    async def test_chat_returns_valid_shape(self) -> None:
        response = await chat(
            ChatRequest(message="What are the admission deadlines?"),
            store=None,
            retriever=FakeRetriever(),
            llm_runner=fake_llm_runner,
        )
        data = response.model_dump()

        assert "conversation_id" in data
        assert "status" in data
        assert "answer_markdown" in data
        assert "citations" in data
        assert data["status"] in ("answered", "not_found", "error")

    @pytest.mark.asyncio
    async def test_chat_preserves_conversation_id(self) -> None:
        cid = uuid.uuid4()
        response = await chat(
            ChatRequest(message="Tell me about CPP", conversation_id=cid),
            store=None,
            retriever=FakeRetriever(),
            llm_runner=fake_llm_runner,
        )
        assert response.conversation_id == str(cid)

    @pytest.mark.asyncio
    async def test_chat_generates_conversation_id(self) -> None:
        response = await chat(
            ChatRequest(message="Hello"),
            store=None,
            retriever=FakeRetriever(),
            llm_runner=fake_llm_runner,
        )
        assert len(response.conversation_id) > 0

    @pytest.mark.asyncio
    async def test_chat_citations_shape(self) -> None:
        response = await chat(
            ChatRequest(message="What are the admission deadlines?"),
            store=None,
            retriever=FakeRetriever(),
            llm_runner=fake_llm_runner,
        )
        data = response.model_dump()
        for citation in data["citations"]:
            assert "title" in citation
            assert "url" in citation
            assert "snippet" in citation

    @pytest.mark.asyncio
    async def test_chat_ambiguous_query_returns_clarification(self) -> None:
        response = await chat(
            ChatRequest(message="hi"),
            store=None,
            retriever=FakeRetriever(),
            llm_runner=fake_llm_runner,
        )
        data = response.model_dump()

        assert data["status"] == "not_found"
        assert data["citations"] == []
        assert "could you give me more detail" in data["answer_markdown"]

    @pytest.mark.asyncio
    async def test_chat_normalized_query_hits_financial_aid_response(self) -> None:
        response = await chat(
            ChatRequest(message="  FAFSA DUE WHEN?? "),
            store=None,
            retriever=FakeRetriever(),
            llm_runner=fake_llm_runner,
        )
        data = response.model_dump()

        assert data["status"] == "answered"
        assert data["citations"][0]["title"] == "Financial Aid and Scholarships"

    def test_chat_rejects_empty_message(self) -> None:
        with pytest.raises(ValidationError):
            ChatRequest(message="")

    def test_chat_rejects_missing_message(self) -> None:
        with pytest.raises(ValidationError):
            ChatRequest.model_validate({})

    def test_chat_rejects_invalid_conversation_id(self) -> None:
        with pytest.raises(ValidationError):
            ChatRequest(message="Hello", conversation_id="not-a-uuid")

    @pytest.mark.asyncio
    async def test_chat_debug_requires_admin_authorization(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await chat(
                ChatRequest(message="Tell me about CPP", debug=True),
                store=None,
                retriever=FakeRetriever(),
                llm_runner=fake_llm_runner,
                admin_debug_authorized=False,
            )

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_chat_debug_returns_debug_info_when_authorized(self) -> None:
        response = await chat(
            ChatRequest(message="Tell me about CPP", debug=True),
            store=None,
            retriever=FakeRetriever(),
            llm_runner=fake_llm_runner,
            admin_debug_authorized=True,
        )

        assert response.debug_info is not None
        assert response.debug_info.raw_query == "Tell me about CPP"
        assert response.debug_info.normalized_query == "tell me about Cal Poly Pomona"
        assert response.debug_info.retrieved_chunks[0].chunk_id == "about-001"

def make_upload(
    payload: bytes,
    *,
    filename: str = "question.webm",
    content_type: str = "audio/webm",
) -> UploadFile:
    return UploadFile(
        file=BytesIO(payload),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


class FakeTranscriber:
    def __init__(self, transcript: str = "Where is the registrar office?") -> None:
        self.transcript = transcript
        self.calls: list[tuple[str, str, bytes]] = []

    async def transcribe(
        self,
        *,
        filename: str,
        content_type: str,
        audio_bytes: bytes,
    ) -> str:
        self.calls.append((filename, content_type, audio_bytes))
        return self.transcript


class MissingConfigTranscriber:
    async def transcribe(
        self,
        *,
        filename: str,
        content_type: str,
        audio_bytes: bytes,
    ) -> str:
        del filename, content_type, audio_bytes
        raise RuntimeError("OPENAI_API_KEY is not configured")


class UpstreamFailureTranscriber:
    async def transcribe(
        self,
        *,
        filename: str,
        content_type: str,
        audio_bytes: bytes,
    ) -> str:
        del filename, content_type, audio_bytes
        raise RuntimeError("provider timeout")


class TestTranscriptionEndpoint:
    @pytest.mark.asyncio
    async def test_transcribe_returns_trimmed_transcript(self) -> None:
        transcriber = FakeTranscriber("  Where is the registrar office?  ")

        response = await transcribe(
            audio=make_upload(b"voice-bytes"),
            settings=Settings(_env_file=None),
            transcriber=transcriber,
        )

        assert response == {"transcript": "Where is the registrar office?"}
        assert transcriber.calls == [
            ("question.webm", "audio/webm", b"voice-bytes"),
        ]

    @pytest.mark.asyncio
    async def test_transcribe_rejects_empty_upload(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await transcribe(
                audio=make_upload(b""),
                settings=Settings(_env_file=None),
                transcriber=FakeTranscriber(),
            )

        assert exc_info.value.status_code == 400
        assert "non-empty audio upload" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_transcribe_rejects_unsupported_media_type(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await transcribe(
                audio=make_upload(
                    b"voice-bytes",
                    filename="question.txt",
                    content_type="text/plain",
                ),
                settings=Settings(_env_file=None),
                transcriber=FakeTranscriber(),
            )

        assert exc_info.value.status_code == 415
        assert "Unsupported audio format" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_transcribe_rejects_oversized_upload(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await transcribe(
                audio=make_upload(b"12345"),
                settings=Settings(
                    _env_file=None,
                    VOICE_TRANSCRIPTION_MAX_BYTES=4,
                ),
                transcriber=FakeTranscriber(),
            )

        assert exc_info.value.status_code == 413
        assert "too large" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_transcribe_maps_missing_configuration_to_503(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await transcribe(
                audio=make_upload(b"voice-bytes"),
                settings=Settings(_env_file=None),
                transcriber=MissingConfigTranscriber(),
            )

        assert exc_info.value.status_code == 503
        assert "unavailable" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_transcribe_maps_upstream_failure_to_503(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await transcribe(
                audio=make_upload(b"voice-bytes"),
                settings=Settings(_env_file=None),
                transcriber=UpstreamFailureTranscriber(),
            )

        assert exc_info.value.status_code == 503
        assert "Please try typing" in str(exc_info.value.detail)
