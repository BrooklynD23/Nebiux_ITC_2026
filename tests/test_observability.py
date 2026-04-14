"""Tests for structured logging helpers."""

from __future__ import annotations

import json
import logging

from src.observability import log_event


def test_log_event_writes_json_with_redaction(caplog) -> None:
    logger = logging.getLogger("tests.observability")

    with caplog.at_level(logging.INFO, logger="tests.observability"):
        log_event(
            logger,
            logging.INFO,
            "chat.request_received",
            conversation_id="cid-123",
            authorization="Bearer secret-token",
            openai_api_key="secret-key",
            llm_prompt_tokens=12,
            raw_query="Tell me about parking",
        )

    payload = json.loads(caplog.records[0].message)
    assert payload["event"] == "chat.request_received"
    assert payload["conversation_id"] == "cid-123"
    assert payload["authorization"] == "[REDACTED]"
    assert payload["openai_api_key"] == "[REDACTED]"
    assert payload["llm_prompt_tokens"] == 12
