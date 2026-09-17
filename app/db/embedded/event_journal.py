from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import aiosqlite

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type  TEXT        NOT NULL,
    payload     TEXT        NOT NULL,
    created_at  TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""
CREATE_IDX = "CREATE INDEX IF NOT EXISTS idx_events_type ON events (event_type, created_at)"


class EventJournalRepository:
    """Append-only event journal stored in a local SQLite file.

    All writes are appends — no UPDATE or DELETE. This makes the journal a
    reliable audit trail for domain events (price fetched, prediction made, etc.)
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def initialize(self) -> None:
        """Create the table and index. Call once at startup."""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(CREATE_SQL)
            await conn.execute(CREATE_IDX)
            await conn.commit()

    async def append(self, event_type: str, payload: dict[str, Any]) -> int:
        """Append a new event and return its auto-incremented id."""
        async with aiosqlite.connect(self.db_path) as conn:
            cur = await conn.execute(
                "INSERT INTO events (event_type, payload) VALUES (?, ?)",
                (event_type, json.dumps(payload)),
            )
            await conn.commit()
            return cur.lastrowid  # type: ignore[return-value]

    async def get_recent(self, event_type: str, n: int = 50) -> list[dict]:
        """Return the *n* most recent events of *event_type*."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cur = await conn.execute(
                "SELECT * FROM events WHERE event_type = ? ORDER BY created_at DESC LIMIT ?",
                (event_type, n),
            )
            rows = await cur.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["payload"] = json.loads(d["payload"])
            result.append(d)
        return result

    async def get_since(self, event_type: str, since: datetime) -> list[dict]:
        """Return all events of *event_type* created after *since*."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cur = await conn.execute(
                "SELECT * FROM events WHERE event_type = ? "
                "AND created_at > ? ORDER BY created_at ASC",
                (event_type, since.isoformat()),
            )
            rows = await cur.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["payload"] = json.loads(d["payload"])
            result.append(d)
        return result
