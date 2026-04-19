"""SQLite-backed conversation memory store."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.agent.support_routing import classify_support_route
from src.conversation.models import (
    ConversationDetail,
    ConversationSummary,
    ConversationTurn,
    Message,
    MessageRole,
    TurnReview,
)
from src.conversation.schema import init_schema


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_ts(raw: str) -> datetime:
    return datetime.fromisoformat(raw)


class ConversationStore:
    """Thread-safe SQLite-backed store for conversation turns."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            str(self._db_path),
            check_same_thread=False,
            isolation_level=None,
        )
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            init_schema(self._conn)

    def get_or_create(self, conversation_id: str | None) -> str:
        """Return an existing conversation id or create a new row."""
        cid = conversation_id or str(uuid.uuid4())
        now = _utcnow_iso()
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO conversations (id, created_at, updated_at)"
                " VALUES (?, ?, ?)"
                " ON CONFLICT(id) DO UPDATE SET updated_at = excluded.updated_at",
                (cid, now, now),
            )
        return cid

    def append_user_message(self, conversation_id: str, content: str) -> Message:
        """Append a user turn and return the persisted Message."""
        return self._append(
            conversation_id=conversation_id,
            role="user",
            content=content,
            citations=None,
            status=None,
        )

    def append_assistant_message(
        self,
        conversation_id: str,
        content: str,
        citations: list[dict],
        status: str,
    ) -> Message:
        """Append an assistant turn and return the persisted Message."""
        return self._append(
            conversation_id=conversation_id,
            role="assistant",
            content=content,
            citations=citations,
            status=status,
        )

    def get_history(self, conversation_id: str, max_turns: int) -> list[Message]:
        """Return the most recent ``2 * max_turns`` messages, oldest first."""
        if max_turns <= 0:
            return []
        limit = 2 * max_turns
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, role, content, citations_json, status, created_at"
                " FROM messages WHERE conversation_id = ?"
                " ORDER BY id DESC LIMIT ?",
                (conversation_id, limit),
            ).fetchall()
        messages = [
            Message(
                id=row["id"],
                role=row["role"],
                content=row["content"],
                created_at=_parse_ts(row["created_at"]),
                citations=(
                    json.loads(row["citations_json"])
                    if row["citations_json"] is not None
                    else None
                ),
                status=row["status"],
            )
            for row in rows
        ]
        messages.reverse()
        return messages

    def append_turn_review(
        self,
        *,
        conversation_id: str,
        user_message_id: int,
        assistant_message_id: int,
        raw_query: str,
        normalized_query: str,
        status: str,
        refusal_trigger: str | None,
        debug_requested: bool,
        debug_authorized: bool,
        llm_prompt_tokens: int | None,
        retrieved_chunks: list[dict],
    ) -> TurnReview:
        """Persist turn-level review metadata for admin inspection."""
        now = _utcnow_iso()
        retrieved_chunks_json = json.dumps(retrieved_chunks)
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO turn_reviews (conversation_id, user_message_id,"
                " assistant_message_id, raw_query, normalized_query, status,"
                " refusal_trigger, debug_requested, debug_authorized,"
                " llm_prompt_tokens, retrieved_chunks_json, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    conversation_id,
                    user_message_id,
                    assistant_message_id,
                    raw_query,
                    normalized_query,
                    status,
                    refusal_trigger,
                    int(debug_requested),
                    int(debug_authorized),
                    llm_prompt_tokens,
                    retrieved_chunks_json,
                    now,
                ),
            )
            self._conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id),
            )
        return TurnReview(
            conversation_id=conversation_id,
            user_message_id=user_message_id,
            assistant_message_id=assistant_message_id,
            raw_query=raw_query,
            normalized_query=normalized_query,
            status=status,
            refusal_trigger=refusal_trigger,
            debug_requested=debug_requested,
            debug_authorized=debug_authorized,
            llm_prompt_tokens=llm_prompt_tokens,
            retrieved_chunks=list(retrieved_chunks),
            created_at=_parse_ts(now),
        )

    def list_conversation_summaries(
        self, *, limit: int, offset: int
    ) -> list[ConversationSummary]:
        """Return recent conversation summaries for the admin dashboard."""
        safe_limit = max(1, min(limit, 100))
        safe_offset = max(0, offset)
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT
                    conversations.id AS conversation_id,
                    conversations.created_at AS created_at,
                    conversations.updated_at AS updated_at,
                    COUNT(turn_reviews.id) AS turn_count,
                    (
                        SELECT status
                        FROM turn_reviews
                        WHERE turn_reviews.conversation_id = conversations.id
                        ORDER BY turn_reviews.id DESC
                        LIMIT 1
                    ) AS last_status,
                    (
                        SELECT content
                        FROM messages
                        WHERE messages.conversation_id = conversations.id
                          AND messages.role = 'user'
                        ORDER BY messages.id DESC
                        LIMIT 1
                    ) AS last_user_message_preview,
                    (
                        SELECT CAST(
                            (julianday(assistant_message.created_at) - julianday(user_message.created_at))
                            * 86400000
                            AS INTEGER
                        )
                        FROM turn_reviews
                        JOIN messages AS user_message
                            ON user_message.id = turn_reviews.user_message_id
                        JOIN messages AS assistant_message
                            ON assistant_message.id = turn_reviews.assistant_message_id
                        WHERE turn_reviews.conversation_id = conversations.id
                        ORDER BY turn_reviews.id DESC
                        LIMIT 1
                    ) AS last_query_latency_ms
                FROM conversations
                LEFT JOIN turn_reviews
                    ON turn_reviews.conversation_id = conversations.id
                GROUP BY conversations.id
                ORDER BY conversations.updated_at DESC
                LIMIT ? OFFSET ?
                """,
                (safe_limit, safe_offset),
            ).fetchall()
        return [
            ConversationSummary(
                conversation_id=row["conversation_id"],
                created_at=_parse_ts(row["created_at"]),
                updated_at=_parse_ts(row["updated_at"]),
                turn_count=row["turn_count"],
                last_status=row["last_status"],
                last_user_message_preview=row["last_user_message_preview"],
                last_query_latency_ms=max(0, row["last_query_latency_ms"])
                if row["last_query_latency_ms"] is not None
                else None,
                is_dangerous_query=(
                    classify_support_route(row["last_user_message_preview"]) is not None
                    if row["last_user_message_preview"]
                    else False
                ),
            )
            for row in rows
        ]

    def get_conversation_detail(
        self, conversation_id: str
    ) -> ConversationDetail | None:
        """Return the transcript and turn reviews for one conversation."""
        with self._lock:
            conversation_row = self._conn.execute(
                "SELECT id, created_at, updated_at" " FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()
            if conversation_row is None:
                return None

            rows = self._conn.execute(
                """
                SELECT
                    turn_reviews.raw_query AS raw_query,
                    turn_reviews.normalized_query AS normalized_query,
                    turn_reviews.status AS review_status,
                    turn_reviews.refusal_trigger AS refusal_trigger,
                    turn_reviews.debug_requested AS debug_requested,
                    turn_reviews.debug_authorized AS debug_authorized,
                    turn_reviews.llm_prompt_tokens AS llm_prompt_tokens,
                    turn_reviews.retrieved_chunks_json AS retrieved_chunks_json,
                    turn_reviews.created_at AS review_created_at,
                    user_message.id AS user_message_id,
                    user_message.role AS user_role,
                    user_message.content AS user_content,
                    user_message.citations_json AS user_citations_json,
                    user_message.status AS user_status,
                    user_message.created_at AS user_created_at,
                    assistant_message.id AS assistant_message_id,
                    assistant_message.role AS assistant_role,
                    assistant_message.content AS assistant_content,
                    assistant_message.citations_json AS assistant_citations_json,
                    assistant_message.status AS assistant_status,
                    assistant_message.created_at AS assistant_created_at
                FROM turn_reviews
                JOIN messages AS user_message
                    ON user_message.id = turn_reviews.user_message_id
                JOIN messages AS assistant_message
                    ON assistant_message.id = turn_reviews.assistant_message_id
                WHERE turn_reviews.conversation_id = ?
                ORDER BY turn_reviews.id ASC
                """,
                (conversation_id,),
            ).fetchall()

        turns = [
            ConversationTurn(
                user_message=Message(
                    id=row["user_message_id"],
                    role=row["user_role"],
                    content=row["user_content"],
                    citations=(
                        json.loads(row["user_citations_json"])
                        if row["user_citations_json"] is not None
                        else None
                    ),
                    status=row["user_status"],
                    created_at=_parse_ts(row["user_created_at"]),
                ),
                assistant_message=Message(
                    id=row["assistant_message_id"],
                    role=row["assistant_role"],
                    content=row["assistant_content"],
                    citations=(
                        json.loads(row["assistant_citations_json"])
                        if row["assistant_citations_json"] is not None
                        else None
                    ),
                    status=row["assistant_status"],
                    created_at=_parse_ts(row["assistant_created_at"]),
                ),
                review=TurnReview(
                    conversation_id=conversation_id,
                    user_message_id=row["user_message_id"],
                    assistant_message_id=row["assistant_message_id"],
                    raw_query=row["raw_query"],
                    normalized_query=row["normalized_query"],
                    status=row["review_status"],
                    refusal_trigger=row["refusal_trigger"],
                    debug_requested=bool(row["debug_requested"]),
                    debug_authorized=bool(row["debug_authorized"]),
                    llm_prompt_tokens=row["llm_prompt_tokens"],
                    retrieved_chunks=json.loads(row["retrieved_chunks_json"]),
                    created_at=_parse_ts(row["review_created_at"]),
                ),
            )
            for row in rows
        ]
        return ConversationDetail(
            conversation_id=conversation_row["id"],
            created_at=_parse_ts(conversation_row["created_at"]),
            updated_at=_parse_ts(conversation_row["updated_at"]),
            turns=turns,
        )

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        with self._lock:
            self._conn.close()

    def _append(
        self,
        *,
        conversation_id: str,
        role: MessageRole,
        content: str,
        citations: list[dict] | None,
        status: str | None,
    ) -> Message:
        now = _utcnow_iso()
        citations_json = json.dumps(citations) if citations is not None else None
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "INSERT INTO messages (conversation_id, role, content,"
                " citations_json, status, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (conversation_id, role, content, citations_json, status, now),
            )
            self._conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id),
            )
        return Message(
            id=cursor.lastrowid,
            role=role,
            content=content,
            created_at=_parse_ts(now),
            citations=citations,
            status=status,
        )
