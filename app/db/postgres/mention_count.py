from __future__ import annotations

from datetime import UTC, datetime

import asyncpg


class MentionCountRepository:
    """Track Reddit mention counts per symbol per subreddit in TimescaleDB.

    Replaces InfluxDB. Table is a TimescaleDB hypertable partitioned by time.
    See init/postgres/009_mention_counts.sql for the schema.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def write(
        self,
        symbol: str,
        subreddit: str,
        count: int,
        avg_score: float = 0.0,
        timestamp: datetime | None = None,
    ) -> None:
        """Write a mention count data point. *timestamp* defaults to now."""
        ts = timestamp or datetime.now(UTC)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO mention_counts (time, symbol, subreddit, count, avg_score)
                VALUES ($1, $2, $3, $4, $5)
                """,
                ts,
                symbol,
                subreddit,
                count,
                avg_score,
            )

    async def get_recent(
        self,
        symbol: str,
        hours: int = 24,
        subreddit: str | None = None,
    ) -> list[dict]:
        """Return mention-count rows for *symbol* over the last *hours*."""
        async with self.pool.acquire() as conn:
            if subreddit:
                rows = await conn.fetch(
                    """
                    SELECT time, symbol, subreddit, count, avg_score
                    FROM mention_counts
                    WHERE symbol = $1
                      AND subreddit = $2
                      AND time >= NOW() - ($3 * INTERVAL '1 hour')
                    ORDER BY time DESC
                    """,
                    symbol,
                    subreddit,
                    hours,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT time, symbol, subreddit, count, avg_score
                    FROM mention_counts
                    WHERE symbol = $1
                      AND time >= NOW() - ($2 * INTERVAL '1 hour')
                    ORDER BY time DESC
                    """,
                    symbol,
                    hours,
                )
            return [dict(row) for row in rows]

    async def get_rolling_total(self, symbol: str, hours: int = 24) -> int:
        """Return the sum of all mention counts for *symbol* over *hours*."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT COALESCE(SUM(count), 0) AS total
                FROM mention_counts
                WHERE symbol = $1
                  AND time >= NOW() - ($2 * INTERVAL '1 hour')
                """,
                symbol,
                hours,
            )
            return int(row["total"])
