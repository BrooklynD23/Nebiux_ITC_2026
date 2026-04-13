"""LLM agent tool loop with hybrid RAG retrieval."""

from __future__ import annotations

import json
import logging
import uuid

from src.agent.prompts import SYSTEM_PROMPT
from src.config import LLMProvider, get_llm_client, get_provider
from src.models import ChatResponse, ChatStatus, Citation, SearchResult
from src.retrieval.hybrid_retriever import HybridRetriever

logger = logging.getLogger(__name__)

# Tool definition sent to the LLM
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
) -> ChatResponse:
    """Process a user message through the agent tool loop.

    Parameters
    ----------
    message:
        The user's natural-language question.
    conversation_id:
        Existing conversation UUID, or None to start fresh.

    Returns
    -------
    ChatResponse
        Grounded answer with citations conforming to the POST /chat contract.
    """
    cid = conversation_id or str(uuid.uuid4())
    provider = get_provider()
    client = get_llm_client()
    retriever = _get_retriever()

    messages: list[dict] = [{"role": "user", "content": message}]
    retrieved: list[SearchResult] = []

    try:
        if provider is LLMProvider.OPENAI:
            answer, retrieved = await _openai_loop(client, messages, retriever)
        else:
            answer, retrieved = await _gemini_loop(client, messages, retriever)
    except Exception as exc:
        logger.exception("Tool loop failed: %s", exc)
        return ChatResponse(
            conversation_id=cid,
            status=ChatStatus.ERROR,
            answer_markdown="Sorry, something went wrong. Please try again.",
            citations=[],
        )

    if not answer:
        return ChatResponse(
            conversation_id=cid,
            status=ChatStatus.NOT_FOUND,
            answer_markdown="I couldn't find information about that in the CPP knowledge base.",
            citations=[],
        )

    citations = _extract_citations(answer, retrieved)

    return ChatResponse(
        conversation_id=cid,
        status=ChatStatus.ANSWERED,
        answer_markdown=answer,
        citations=citations,
    )


async def _openai_loop(
    client,
    messages: list[dict],
    retriever: HybridRetriever,
) -> tuple[str, list[SearchResult]]:
    """Run the OpenAI tool-calling loop."""
    from openai import OpenAI

    all_retrieved: list[SearchResult] = []
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    while True:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=full_messages,
            tools=[_SEARCH_TOOL],
            tool_choice="auto",
        )

        choice = response.choices[0]

        # LLM is done — return its final answer
        if choice.finish_reason == "stop":
            return choice.message.content or "", all_retrieved

        # LLM wants to call search_corpus
        if choice.finish_reason == "tool_calls":
            full_messages.append(choice.message)

            for tool_call in choice.message.tool_calls:
                args = json.loads(tool_call.function.arguments)
                query = args["query"]
                top_k = args.get("top_k", 5)

                logger.info("search_corpus(%r, top_k=%d)", query, top_k)
                results = await retriever.search_corpus(query, top_k=top_k)
                all_retrieved.extend(results)

                tool_result = _format_results_for_llm(results)
                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                })

            continue

        # Unexpected finish reason
        break

    return "", all_retrieved


async def _gemini_loop(
    client,
    messages: list[dict],
    retriever: HybridRetriever,
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

    contents = [types.Content(role="user", parts=[types.Part(text=messages[-1]["content"])])]
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

        # Check if any part is a function call
        tool_calls = [p for p in candidate.content.parts if p.function_call]

        if not tool_calls:
            # No tool calls — final answer
            text_parts = [p.text for p in candidate.content.parts if hasattr(p, "text") and p.text]
            return "\n".join(text_parts), all_retrieved

        # Execute each tool call and append results
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


def _format_results_for_llm(results: list[SearchResult]) -> str:
    """Format retrieved chunks as a readable string for the LLM context."""
    if not results:
        return "No results found."

    parts = []
    for i, r in enumerate(results, 1):
        parts.append(
            f"[{i}] {r.title}\nURL: {r.url}\n{r.snippet}"
        )
    return "\n\n".join(parts)


def _extract_citations(answer: str, retrieved: list[SearchResult]) -> list[Citation]:
    """Return citations for sources the LLM actually referenced in its answer."""
    if not retrieved:
        return []

    seen_urls: set[str] = set()
    citations: list[Citation] = []

    for result in retrieved:
        if result.url in seen_urls:
            continue
        # Include citation if the URL or title appears in the answer
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
