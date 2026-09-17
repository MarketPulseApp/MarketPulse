from __future__ import annotations

from datetime import UTC, datetime

import asyncpg


class APICallLogRepository:
    """Append-only log of outbound API calls stored in PostgreSQL.

    Replaces DataStax Astra (Cassandra). Uses a simple append-only table;
    old rows are pruned by a pg_cron job or TimescaleDB retention policy.
    See init/postgres/009_mention_counts.sql for the table definition.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def log(
        self,
        source: str,
        endpoint: str,
        status_code: int,
        latency_ms: int,
        error_msg: str | None = None,
    ) -> None:
        """Fire-and-forget: append a log entry."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO api_call_log
                    (source, logged_at, endpoint, status_code, latency_ms, error_msg)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                source,
                datetime.now(UTC),
                endpoint,
                status_code,
                latency_ms,
                error_msg,
            )

    async def get_recent(self, source: str, limit: int = 100) -> list[dict]:
        """Return the most recent *limit* log entries for *source*."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT source, logged_at, endpoint, status_code, latency_ms, error_msg
                FROM api_call_log
                WHERE source = $1
                ORDER BY logged_at DESC
                LIMIT $2
                """,
                source,
                limit,
            )
            return [dict(row) for row in rows]
