"""LLM agent tool loop with hybrid RAG retrieval."""

from __future__ import annotations

import json
import logging
import uuid
from typing import TYPE_CHECKING

from fastapi import HTTPException

from src.agent.prompts import SYSTEM_PROMPT
from src.agent.query_normalizer import normalize
from src.config import LLMProvider, get_llm_client, get_provider
from src.models import ChatResponse, ChatStatus, Citation, SearchResult
from src.retrieval.hybrid_retriever import HybridRetriever

if TYPE_CHECKING:
    from src.conversation import ConversationStore, Message

logger = logging.getLogger(__name__)

_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_corpus",
        "description": "Search the Cal Poly Pomona knowledge base for relevant information.",
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

_retriever: HybridRetriever | None = None


def _get_retriever() -> HybridRetriever:
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever


async def run_tool_loop(
    message: str,
    conversation_id: str | None = None,
    *,
    store: "ConversationStore | None" = None,
    max_turns: int = 10,
) -> ChatResponse:
    """Process a user message through the agent tool loop.

    When ``store`` is provided, the prior history is loaded, the new
    user turn is persisted before generation, and the assistant turn is
    persisted afterwards.  When ``store`` is ``None`` the function
    still returns a valid response (used by legacy contract tests).
    """
    if store is not None:
        cid = store.get_or_create(conversation_id)
    else:
        cid = conversation_id or str(uuid.uuid4())

    history: "list[Message]" = []
    if store is not None:
        history = store.get_history(cid, max_turns=max_turns)
        try:
            store.append_user_message(cid, message)
        except Exception:
            logger.exception(
                "Failed to persist user message for conversation %s", cid
            )
            raise HTTPException(
                status_code=500,
                detail="Conversation store unavailable",
            ) from None

    normalized = normalize(message)
    logger.debug(
        "query raw=%r normalized=%r ambiguous=%s",
        normalized.original,
        normalized.normalized_text,
        normalized.is_ambiguous,
    )

    if normalized.is_ambiguous:
        response = ChatResponse(
            conversation_id=cid,
            status=ChatStatus.NOT_FOUND,
            answer_markdown=(
                "Your question is a bit short — could you give me more detail? "
                "For example: *\"What are the FAFSA deadlines at CPP?\"* or "
                "*\"Where is the financial aid office?\"*"
            ),
            citations=[],
        )
    else:
        response = await _run_llm_loop(normalized.normalized_text, cid, history)

    if store is not None:
        try:
            store.append_assistant_message(
                cid,
                response.answer_markdown,
                [c.model_dump() for c in response.citations],
                response.status.value,
            )
        except Exception:
            logger.exception(
                "Failed to persist assistant message for conversation %s", cid
            )

    return response


async def _run_llm_loop(
    message: str,
    conversation_id: str,
    history: "list[Message]",
) -> ChatResponse:
    """Run the real LLM tool-calling loop with hybrid retrieval."""
    provider = get_provider()
    client = get_llm_client()
    retriever = _get_retriever()

    messages: list[dict] = [{"role": "user", "content": message}]
    retrieved: list[SearchResult] = []

    try:
        if provider is LLMProvider.OPENAI:
            answer, retrieved = await _openai_loop(client, messages, retriever, history)
        else:
            answer, retrieved = await _gemini_loop(client, messages, retriever, history)
    except Exception as exc:
        logger.exception("Tool loop failed: %s", exc)
        return ChatResponse(
            conversation_id=conversation_id,
            status=ChatStatus.ERROR,
            answer_markdown="Sorry, something went wrong. Please try again.",
            citations=[],
        )

    if not answer:
        return ChatResponse(
            conversation_id=conversation_id,
            status=ChatStatus.NOT_FOUND,
            answer_markdown="I couldn't find information about that in the CPP knowledge base.",
            citations=[],
        )

    return ChatResponse(
        conversation_id=conversation_id,
        status=ChatStatus.ANSWERED,
        answer_markdown=answer,
        citations=_extract_citations(answer, retrieved),
    )


async def _openai_loop(
    client,
    messages: list[dict],
    retriever: HybridRetriever,
    history: "list[Message]",
) -> tuple[str, list[SearchResult]]:
    """Run the OpenAI tool-calling loop."""
    all_retrieved: list[SearchResult] = []

    full_messages = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + _history_to_openai(history)
        + messages
    )

    while True:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=full_messages,
            tools=[_SEARCH_TOOL],
            tool_choice="auto",
        )

        choice = response.choices[0]

        if choice.finish_reason == "stop":
            return choice.message.content or "", all_retrieved

        if choice.finish_reason == "tool_calls":
            full_messages.append(choice.message)

            for tool_call in choice.message.tool_calls:
                args = json.loads(tool_call.function.arguments)
                query = args["query"]
                top_k = args.get("top_k", 5)

                logger.info("search_corpus(%r, top_k=%d)", query, top_k)
                results = await retriever.search_corpus(query, top_k=top_k)
                all_retrieved.extend(results)

                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": _format_results_for_llm(results),
                })

            continue

        break

    return "", all_retrieved


async def _gemini_loop(
    client,
    messages: list[dict],
    retriever: HybridRetriever,
    history: "list[Message]",
) -> tuple[str, list[SearchResult]]:
    """Run the Gemini tool-calling loop."""
    from google.genai import types  # type: ignore[import-untyped]

    all_retrieved: list[SearchResult] = []

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
        types.Content(role="user", parts=[types.Part(text=messages[-1]["content"])])
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

        tool_calls = [p for p in candidate.content.parts if p.function_call]

        if not tool_calls:
            text_parts = [
                p.text for p in candidate.content.parts
                if hasattr(p, "text") and p.text
            ]
            return "\n".join(text_parts), all_retrieved

        tool_results = []
        for part in tool_calls:
            fc = part.function_call
            query = fc.args.get("query", "")
            top_k = fc.args.get("top_k", 5)

            logger.info("search_corpus(%r, top_k=%d)", query, top_k)
            results = await retriever.search_corpus(query, top_k=top_k)
            all_retrieved.extend(results)

            tool_results.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        name="search_corpus",
                        response={"result": _format_results_for_llm(results)},
                    )
                )
            )

        contents.append(types.Content(role="tool", parts=tool_results))

    return "", all_retrieved


def _history_to_openai(history: "list[Message]") -> list[dict]:
    messages = []
    for turn in history:
        messages.append({"role": "user", "content": turn.user_text})
        messages.append({"role": "assistant", "content": turn.assistant_text})
    return messages


def _history_to_gemini(history: "list[Message]", types) -> list:
    contents = []
    for turn in history:
        contents.append(
            types.Content(role="user", parts=[types.Part(text=turn.user_text)])
        )
        contents.append(
            types.Content(role="model", parts=[types.Part(text=turn.assistant_text)])
        )
    return contents


def _format_results_for_llm(results: list[SearchResult]) -> str:
    if not results:
        return "No results found."
    parts = []
    for i, r in enumerate(results, 1):
        parts.append(f"[{i}] {r.title}\nURL: {r.url}\n{r.snippet}")
    return "\n\n".join(parts)


def _extract_citations(answer: str, retrieved: list[SearchResult]) -> list[Citation]:
    if not retrieved:
        return []

    seen_urls: set[str] = set()
    citations: list[Citation] = []

    for result in retrieved:
        if result.url in seen_urls:
            continue
        if result.url in answer or result.title in answer:
            citations.append(
                Citation(
                    title=result.title,
                    url=result.url,
                    snippet=result.snippet,
                )
            )
            seen_urls.add(result.url)

    return citations
