"""LLM agent tool loop with hybrid retrieval and grounding gates."""

from __future__ import annotations

import json
import logging
import re
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fastapi import HTTPException

from src.agent.grounding import (
    GroundingVerdict,
    RefusalContext,
    assess_confidence,
    build_refusal_response,
)
from src.agent.query_normalizer import normalize
from src.agent.support_routing import (
    SupportRoute,
    build_support_response,
    classify_support_route,
)
from src.agent.system_prompt import SYSTEM_PROMPT
from src.citations import normalize_url
from src.config import LLMProvider, get_llm_client, get_provider
from src.models import (
    ChatDebugInfo,
    ChatResponse,
    ChatStatus,
    Citation,
    RetrievedChunkDebug,
    SearchResult,
)
from src.observability import log_event
from src.retrieval.interface import RetrieverBase
from src.settings import get_settings

if TYPE_CHECKING:
    from src.conversation import ConversationStore, Message

logger = logging.getLogger(__name__)

_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_corpus",
        "description": (
            "Search the Cal Poly Pomona knowledge base for relevant "
            "information."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A concise natural-language search query.",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (default 5).",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
}
_SOURCES_HEADER_RE = re.compile(
    r"\n(?:\*\*)?sources:(?:\*\*)?\s*\n",
    re.IGNORECASE,
)
_SOURCE_LINE_RE = re.compile(
    r"^- \[(?P<title>[^\]]+)\]\((?P<url>[^)]+)\)",
    re.MULTILINE,
)
_default_retriever: RetrieverBase | None = None


@dataclass(frozen=True)
class ToolLoopExecution:
    """Structured result returned by a provider loop."""

    answer_markdown: str = ""
    retrieved: list[SearchResult] = field(default_factory=list)
    grounding_verdict: GroundingVerdict | None = None
    grounding_query: str | None = None
    prompt_tokens: int | None = None


ToolLoopRunner = Callable[
    [str, list["Message"], RetrieverBase],
    Awaitable[ToolLoopExecution],
]


async def run_tool_loop(
    message: str,
    conversation_id: str | None = None,
    *,
    store: "ConversationStore | None" = None,
    max_turns: int = 10,
    retriever: RetrieverBase | None = None,
    llm_runner: ToolLoopRunner | None = None,
    debug_requested: bool = False,
    debug_authorized: bool = False,
) -> ChatResponse:
    """Process a user message through the agent tool loop."""
    if store is not None:
        cid = store.get_or_create(conversation_id)
    else:
        cid = conversation_id or str(uuid.uuid4())

    history: list[Message] = []
    user_message = None
    if store is not None:
        history = store.get_history(cid, max_turns=max_turns)
        try:
            user_message = store.append_user_message(cid, message)
        except Exception:
            logger.exception(
                "Failed to persist user message for conversation %s",
                cid,
            )
            raise HTTPException(
                status_code=500,
                detail="Conversation store unavailable",
            ) from None

    normalized = normalize(message)
    log_event(
        logger,
        logging.INFO,
        "chat.request_received",
        conversation_id=cid,
        raw_query=message,
        normalized_query=normalized.normalized_text,
        debug_requested=debug_requested,
        debug_authorized=debug_authorized,
        ambiguous=normalized.is_ambiguous,
    )

    execution = ToolLoopExecution()
    refusal_trigger: str | None = None
    route = classify_support_route(message)
    active_retriever = retriever or _get_default_retriever()

    if route is not None:
        if active_retriever is None:
            response = ChatResponse(
                conversation_id=cid,
                status=ChatStatus.ERROR,
                answer_markdown=(
                    "The retrieval backend is not ready yet. Build the search "
                    "artifacts and restart the API."
                ),
                citations=[],
            )
        else:
            response, execution, refusal_trigger = await _run_support_route(
                cid,
                route.retrieval_query,
                route,
                active_retriever,
            )
    elif normalized.is_ambiguous:
        refusal_trigger = "query.ambiguous"
        response = ChatResponse(
            conversation_id=cid,
            status=ChatStatus.NOT_FOUND,
            answer_markdown=(
                "Your question is a bit short — could you give me more detail? "
                'For example: *"What are the FAFSA deadlines at CPP?"* or '
                '*"Where is the financial aid office?"*'
            ),
            citations=[],
        )
    else:
        active_runner = llm_runner or _run_llm_loop

        if active_retriever is None:
            response = ChatResponse(
                conversation_id=cid,
                status=ChatStatus.ERROR,
                answer_markdown=(
                    "The retrieval backend is not ready yet. Build the search "
                    "artifacts and restart the API."
                ),
                citations=[],
            )
        else:
            try:
                execution = await active_runner(
                    normalized.normalized_text,
                    history,
                    active_retriever,
                )
                log_event(
                    logger,
                    logging.INFO,
                    "chat.retrieval_completed",
                    conversation_id=cid,
                    normalized_query=normalized.normalized_text,
                    retrieved_chunks=_serialize_retrieved_chunks(execution.retrieved),
                    llm_prompt_tokens=execution.prompt_tokens,
                )
            except Exception as exc:
                logger.exception("Tool loop failed: %s", exc)
                response = ChatResponse(
                    conversation_id=cid,
                    status=ChatStatus.ERROR,
                    answer_markdown=(
                        "Sorry, something went wrong. Please try again."
                    ),
                    citations=[],
                )
            else:
                response, refusal_trigger = _build_response_from_execution(
                    cid,
                    normalized.normalized_text,
                    execution,
                )

    if refusal_trigger is not None:
        log_event(
            logger,
            logging.INFO,
            "chat.refusal_triggered",
            conversation_id=cid,
            refusal_trigger=refusal_trigger,
            normalized_query=normalized.normalized_text,
        )

    if debug_requested and debug_authorized:
        response.debug_info = ChatDebugInfo(
            raw_query=message,
            normalized_query=normalized.normalized_text,
            retrieved_chunks=[
                RetrievedChunkDebug.model_validate(chunk)
                for chunk in _serialize_retrieved_chunks(execution.retrieved)
            ],
            refusal_trigger=refusal_trigger,
            llm_prompt_tokens=execution.prompt_tokens,
        )

    assistant_message = None
    if store is not None:
        try:
            assistant_message = store.append_assistant_message(
                cid,
                response.answer_markdown,
                [citation.model_dump() for citation in response.citations],
                response.status.value,
            )
        except Exception:
            logger.exception(
                "Failed to persist assistant message for conversation %s",
                cid,
            )
        else:
            append_turn_review = getattr(store, "append_turn_review", None)
            if user_message is not None and callable(append_turn_review):
                try:
                    append_turn_review(
                        conversation_id=cid,
                        user_message_id=user_message.id,
                        assistant_message_id=assistant_message.id,
                        raw_query=message,
                        normalized_query=normalized.normalized_text,
                        status=response.status.value,
                        refusal_trigger=refusal_trigger,
                        debug_requested=debug_requested,
                        debug_authorized=debug_authorized,
                        llm_prompt_tokens=execution.prompt_tokens,
                        retrieved_chunks=_serialize_retrieved_chunks(
                            execution.retrieved
                        ),
                    )
                except Exception:
                    logger.exception(
                        "Failed to persist turn review for conversation %s",
                        cid,
                    )

    log_event(
        logger,
        logging.INFO,
        "chat.response_completed",
        conversation_id=cid,
        status=response.status.value,
        citation_count=len(response.citations),
        debug_info_included=response.debug_info is not None,
    )

    return response


async def _run_support_route(
    conversation_id: str,
    retrieval_query: str,
    route: SupportRoute,
    retriever: RetrieverBase,
) -> tuple[ChatResponse, ToolLoopExecution, str | None]:
    """Route high-support messages to a deterministic cited CPP service."""
    results = await retriever.search_corpus(retrieval_query, top_k=3)
    verdict = assess_confidence(results, get_settings().grounding_config)
    if not verdict.grounded:
        execution = ToolLoopExecution(
            retrieved=list(results),
            grounding_verdict=verdict,
            grounding_query=retrieval_query,
        )
        log_event(
            logger,
            logging.INFO,
            "chat.retrieval_completed",
            conversation_id=conversation_id,
            retrieval_query=retrieval_query,
            route_id=route.route_id,
            retrieved_chunks=_serialize_retrieved_chunks(execution.retrieved),
            llm_prompt_tokens=execution.prompt_tokens,
        )
        return (
            build_refusal_response(
                conversation_id,
                verdict,
                RefusalContext(normalized_query=retrieval_query),
            ),
            execution,
            verdict.reason,
        )

    execution = ToolLoopExecution(retrieved=list(results))
    log_event(
        logger,
        logging.INFO,
        "chat.retrieval_completed",
        conversation_id=conversation_id,
        retrieval_query=retrieval_query,
        route_id=route.route_id,
        retrieved_chunks=_serialize_retrieved_chunks(execution.retrieved),
        llm_prompt_tokens=execution.prompt_tokens,
    )
    return (
        build_support_response(conversation_id, route, results),
        execution,
        None,
    )


async def _run_llm_loop(
    message: str,
    history: list[Message],
    retriever: RetrieverBase,
) -> ToolLoopExecution:
    """Run the configured provider loop."""
    provider = get_provider()
    client = get_llm_client()

    if provider is LLMProvider.OPENAI:
        return await _openai_loop(client, message, history, retriever)

    return await _gemini_loop(client, message, history, retriever)


async def _openai_loop(
    client: object,
    message: str,
    history: list[Message],
    retriever: RetrieverBase,
) -> ToolLoopExecution:
    """Run the OpenAI tool-calling loop."""
    all_retrieved: list[SearchResult] = []
    full_messages = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + _history_to_openai(history)
        + [{"role": "user", "content": message}]
    )
    grounding_checked = False

    while True:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=full_messages,
            tools=[_SEARCH_TOOL],
            tool_choice="auto",
        )
        choice = response.choices[0]

        if choice.finish_reason == "stop":
            return ToolLoopExecution(
                answer_markdown=choice.message.content or "",
                retrieved=all_retrieved,
                prompt_tokens=None,
            )

        if choice.finish_reason == "tool_calls":
            full_messages.append(choice.message)

            for tool_call in choice.message.tool_calls:
                args = json.loads(tool_call.function.arguments)
                query = args["query"]
                top_k = args.get("top_k", 5)

                logger.info("search_corpus(%r, top_k=%d)", query, top_k)
                results = await retriever.search_corpus(query, top_k=top_k)
                all_retrieved.extend(results)

                if not grounding_checked:
                    grounding_checked = True
                    failure = _weak_retrieval_execution(query, results)
                    if failure is not None:
                        return failure

                full_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": _format_results_for_llm(results),
                    }
                )

            continue

        break

    return ToolLoopExecution(retrieved=all_retrieved, prompt_tokens=None)


async def _gemini_loop(
    client: object,
    message: str,
    history: list[Message],
    retriever: RetrieverBase,
) -> ToolLoopExecution:
    """Run the Gemini tool-calling loop."""
    from google.genai import types  # type: ignore[import-untyped]

    all_retrieved: list[SearchResult] = []
    grounding_checked = False
    gemini_tool = types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="search_corpus",
                description=_SEARCH_TOOL["function"]["description"],
                parameters=types.Schema(
                    type="OBJECT",
                    properties={
                        "query": types.Schema(type="STRING"),
                        "top_k": types.Schema(type="INTEGER"),
                    },
                    required=["query"],
                ),
            )
        ]
    )
    contents = _history_to_gemini(history, types) + [
        types.Content(role="user", parts=[types.Part(text=message)])
    ]
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[gemini_tool],
    )

    while True:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=config,
        )
        candidate = response.candidates[0]
        contents.append(candidate.content)

        tool_calls = [part for part in candidate.content.parts if part.function_call]
        if not tool_calls:
            text_parts = [
                part.text
                for part in candidate.content.parts
                if hasattr(part, "text") and part.text
            ]
            return ToolLoopExecution(
                answer_markdown="\n".join(text_parts),
                retrieved=all_retrieved,
                prompt_tokens=None,
            )

        tool_results = []
        for part in tool_calls:
            function_call = part.function_call
            query = function_call.args.get("query", "")
            top_k = function_call.args.get("top_k", 5)

            logger.info("search_corpus(%r, top_k=%d)", query, top_k)
            results = await retriever.search_corpus(query, top_k=top_k)
            all_retrieved.extend(results)

            if not grounding_checked:
                grounding_checked = True
                failure = _weak_retrieval_execution(query, results)
                if failure is not None:
                    return failure

            tool_results.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        name="search_corpus",
                        response={"result": _format_results_for_llm(results)},
                    )
                )
            )

        contents.append(types.Content(role="tool", parts=tool_results))


def _build_response_from_execution(
    conversation_id: str,
    normalized_query: str,
    execution: ToolLoopExecution,
) -> tuple[ChatResponse, str | None]:
    if (
        execution.grounding_verdict is not None
        and not execution.grounding_verdict.grounded
    ):
        refusal_query = execution.grounding_query or normalized_query
        return (
            build_refusal_response(
                conversation_id,
                execution.grounding_verdict,
                RefusalContext(normalized_query=refusal_query),
            ),
            execution.grounding_verdict.reason,
        )

    if not execution.answer_markdown:
        return (
            ChatResponse(
                conversation_id=conversation_id,
                status=ChatStatus.NOT_FOUND,
                answer_markdown=(
                    "I couldn't find information about that in the CPP knowledge base."
                ),
                citations=[],
            ),
            "retrieval.no_answer",
        )

    answer_body, citations = _extract_answer_and_citations(
        execution.answer_markdown,
        execution.retrieved,
    )
    return (
        ChatResponse(
            conversation_id=conversation_id,
            status=ChatStatus.ANSWERED,
            answer_markdown=answer_body,
            citations=citations,
        ),
        None,
    )


def _weak_retrieval_execution(
    query: str,
    results: list[SearchResult],
) -> ToolLoopExecution | None:
    verdict = assess_confidence(results, get_settings().grounding_config)
    if verdict.grounded:
        return None
    return ToolLoopExecution(
        retrieved=list(results),
        grounding_verdict=verdict,
        grounding_query=normalize(query).normalized_text,
    )


def _get_default_retriever() -> RetrieverBase | None:
    global _default_retriever
    if _default_retriever is not None:
        return _default_retriever

    try:
        from src.retrieval.hybrid_retriever import HybridRetriever

        _default_retriever = HybridRetriever()
        return _default_retriever
    except Exception:
        logger.exception("Failed to initialize HybridRetriever")

    try:
        from src.retrieval.whoosh_retriever import WhooshRetriever

        _default_retriever = WhooshRetriever()
        return _default_retriever
    except Exception:
        logger.exception("Failed to initialize WhooshRetriever")
        return None


def _history_to_openai(history: list[Message]) -> list[dict[str, str]]:
    return [
        {
            "role": "assistant" if turn.role == "assistant" else "user",
            "content": turn.content,
        }
        for turn in history
    ]


def _history_to_gemini(history: list[Message], types: object) -> list[object]:
    contents = []
    for turn in history:
        role = "model" if turn.role == "assistant" else "user"
        contents.append(
            types.Content(role=role, parts=[types.Part(text=turn.content)])
        )
    return contents


def _format_results_for_llm(results: list[SearchResult]) -> str:
    if not results:
        return "No results found."

    parts = []
    for index, result in enumerate(results, start=1):
        parts.append(
            "\n".join(
                [
                    f"[{index}] {result.title}",
                    f"URL: {result.url}",
                    f"Snippet: {result.snippet}",
                    f"Chunk ID: {result.chunk_id}",
                ]
            )
        )
    return "\n\n".join(parts)


def _extract_answer_and_citations(
    answer: str,
    retrieved: list[SearchResult],
) -> tuple[str, list[Citation]]:
    body, footer = _split_sources_footer(answer)
    citations = _extract_citations_from_footer(footer, retrieved)
    if not citations:
        citations = _extract_citations_from_text(answer, retrieved)
    cleaned_body = body.strip() or answer.strip()
    return cleaned_body, citations


def _split_sources_footer(answer: str) -> tuple[str, str]:
    match = _SOURCES_HEADER_RE.search(answer)
    if match is None:
        return answer, ""
    return answer[: match.start()].rstrip(), answer[match.end() :].strip()


def _extract_citations_from_footer(
    footer: str,
    retrieved: list[SearchResult],
) -> list[Citation]:
    if not footer or not retrieved:
        return []

    by_url = {normalize_url(result.url): result for result in retrieved}
    by_title = {result.title.lower(): result for result in retrieved}
    seen_urls: set[str] = set()
    citations: list[Citation] = []

    for match in _SOURCE_LINE_RE.finditer(footer):
        normalized_footer_url = normalize_url(match.group("url"))
        title = match.group("title").strip().lower()
        result = by_url.get(normalized_footer_url) or by_title.get(title)
        if result is None or result.url in seen_urls:
            continue
        citations.append(
            Citation(
                title=result.title,
                url=result.url,
                snippet=result.snippet,
            )
        )
        seen_urls.add(result.url)

    return citations


def _extract_citations_from_text(
    answer: str,
    retrieved: list[SearchResult],
) -> list[Citation]:
    if not retrieved:
        return []

    seen_urls: set[str] = set()
    citations: list[Citation] = []
    lower_answer = answer.lower()

    for result in retrieved:
        if result.url in seen_urls:
            continue
        if result.url in answer or result.title.lower() in lower_answer:
            citations.append(
                Citation(
                    title=result.title,
                    url=result.url,
                    snippet=result.snippet,
                )
            )
            seen_urls.add(result.url)

    return citations


def _serialize_retrieved_chunks(
    results: list[SearchResult],
) -> list[dict[str, object]]:
    return [
        {
            "chunk_id": result.chunk_id,
            "title": result.title,
            "section": result.section,
            "url": result.url,
            "snippet": result.snippet,
            "score": result.score,
        }
        for result in results
    ]
