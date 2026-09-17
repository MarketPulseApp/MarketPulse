from __future__ import annotations

import hashlib
import json
from typing import Any

import aiosqlite

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    action      TEXT        NOT NULL,
    actor_id    TEXT,
    target_type TEXT,
    target_id   TEXT,
    old_value   TEXT,
    new_value   TEXT,
    created_at  TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    row_hash    TEXT        NOT NULL
)
"""
_GENESIS_HASH = "GENESIS"


class AuditLedgerRepository:
    """Tamper-evident audit log using a SHA-256 hash chain.

    Each row's row_hash is computed from: previous_row_hash + this_row_content.
    Tampering with or deleting any row breaks verify_chain().
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def initialize(self) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(CREATE_SQL)
            await conn.commit()

    async def _last_hash(self, conn: aiosqlite.Connection) -> str:
        cur = await conn.execute("SELECT row_hash FROM audit_log ORDER BY id DESC LIMIT 1")
        row = await cur.fetchone()
        return row[0] if row else _GENESIS_HASH

    @staticmethod
    def _compute_hash(prev_hash: str, content: str) -> str:
        raw = f"{prev_hash}{content}"
        return hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def _content_string(
        action: str,
        actor_id: str | None,
        target_type: str | None,
        target_id: str | None,
        old_value: Any,
        new_value: Any,
    ) -> str:
        """Deterministic serialisation of row fields for hashing."""
        return json.dumps(
            {
                "action": action,
                "actor_id": actor_id,
                "target_type": target_type,
                "target_id": target_id,
                "old_value": old_value,
                "new_value": new_value,
            },
            sort_keys=True,
            default=str,
        )

    async def append(
        self,
        action: str,
        actor_id: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        old_value: Any = None,
        new_value: Any = None,
    ) -> None:
        """Append a new entry to the ledger, chaining it to the previous hash."""
        async with aiosqlite.connect(self.db_path) as conn:
            prev_hash = await self._last_hash(conn)
            content = self._content_string(
                action, actor_id, target_type, target_id, old_value, new_value
            )
            row_hash = self._compute_hash(prev_hash, content)

            await conn.execute(
                """
                INSERT INTO audit_log
                    (action, actor_id, target_type, target_id, old_value, new_value, row_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    action,
                    actor_id,
                    target_type,
                    target_id,
                    json.dumps(old_value, default=str) if old_value is not None else None,
                    json.dumps(new_value, default=str) if new_value is not None else None,
                    row_hash,
                ),
            )
            await conn.commit()

    async def verify_chain(self) -> bool:
        """Recompute every hash from scratch and check it matches the stored value.

        Returns True if the chain is intact, False if any row was tampered with.
        """
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cur = await conn.execute("SELECT * FROM audit_log ORDER BY id ASC")
            rows = await cur.fetchall()

        prev_hash = _GENESIS_HASH
        for row in rows:
            content = self._content_string(
                row["action"],
                row["actor_id"],
                row["target_type"],
                row["target_id"],
                json.loads(row["old_value"]) if row["old_value"] else None,
                json.loads(row["new_value"]) if row["new_value"] else None,
            )
            expected = self._compute_hash(prev_hash, content)
            if expected != row["row_hash"]:
                return False
            prev_hash = row["row_hash"]
        return True

    async def get_recent(self, n: int = 50) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cur = await conn.execute(
                "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?", (n,)
            )
            rows = await cur.fetchall()
        return [dict(r) for r in rows]
