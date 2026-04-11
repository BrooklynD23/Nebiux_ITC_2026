"""SQLite-backed conversation memory store."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.conversation.models import Message
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
            row = self._conn.execute(
                "SELECT id FROM conversations WHERE id = ?",
                (cid,),
            ).fetchone()
            if row is None:
                self._conn.execute(
                    "INSERT INTO conversations (id, created_at, updated_at)"
                    " VALUES (?, ?, ?)",
                    (cid, now, now),
                )
            else:
                self._conn.execute(
                    "UPDATE conversations SET updated_at = ? WHERE id = ?",
                    (now, cid),
                )
        return cid

    def append_user_message(
        self, conversation_id: str, content: str
    ) -> Message:
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

    def get_history(
        self, conversation_id: str, max_turns: int
    ) -> list[Message]:
        """Return the most recent ``2 * max_turns`` messages, oldest first."""
        if max_turns <= 0:
            return []
        limit = 2 * max_turns
        with self._lock:
            rows = self._conn.execute(
                "SELECT role, content, citations_json, status, created_at"
                " FROM messages WHERE conversation_id = ?"
                " ORDER BY id DESC LIMIT ?",
                (conversation_id, limit),
            ).fetchall()
        messages = [
            Message(
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

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        with self._lock:
            self._conn.close()

    def _append(
        self,
        *,
        conversation_id: str,
        role: str,
        content: str,
        citations: list[dict] | None,
        status: str | None,
    ) -> Message:
        now = _utcnow_iso()
        citations_json = (
            json.dumps(citations) if citations is not None else None
        )
        with self._lock, self._conn:
            self._conn.execute(
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
            role=role,  # type: ignore[arg-type]
            content=content,
            created_at=_parse_ts(now),
            citations=citations,
            status=status,
        )
