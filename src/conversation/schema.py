"""SQLite schema for conversation memory."""

from __future__ import annotations

import sqlite3

_DDL = (
    """
    CREATE TABLE IF NOT EXISTS conversations (
        id         TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS messages (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
        role            TEXT NOT NULL CHECK (role IN ('user','assistant')),
        content         TEXT NOT NULL,
        citations_json  TEXT,
        status          TEXT,
        created_at      TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_messages_conv_id
        ON messages (conversation_id, id)
    """,
    """
    CREATE TABLE IF NOT EXISTS turn_reviews (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id     TEXT NOT NULL REFERENCES conversations(id)
                               ON DELETE CASCADE,
        user_message_id     INTEGER NOT NULL REFERENCES messages(id)
                               ON DELETE CASCADE,
        assistant_message_id INTEGER NOT NULL REFERENCES messages(id)
                               ON DELETE CASCADE,
        raw_query           TEXT NOT NULL,
        normalized_query    TEXT NOT NULL,
        status              TEXT NOT NULL,
        refusal_trigger     TEXT,
        debug_requested     INTEGER NOT NULL,
        debug_authorized    INTEGER NOT NULL,
        llm_prompt_tokens   INTEGER,
        retrieved_chunks_json TEXT NOT NULL,
        created_at          TEXT NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_turn_reviews_conv_id
        ON turn_reviews (conversation_id, id)
    """,
)


def init_schema(conn: sqlite3.Connection) -> None:
    """Create tables and indexes if they do not exist."""
    with conn:
        for statement in _DDL:
            conn.execute(statement)
