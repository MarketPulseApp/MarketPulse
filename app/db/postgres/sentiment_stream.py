from __future__ import annotations

from datetime import UTC, datetime

import asyncpg


class SentimentStreamRepository:
    """Real-time intraday sentiment writes — TimescaleDB hypertable."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def write(self, symbol: str, source: str, score: float) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO sentiment_stream (time, symbol, source, score) VALUES ($1, $2, $3, $4)",
                datetime.now(UTC),
                symbol,
                source,
                score,
            )

    async def get_realtime(self, symbol: str, minutes: int = 60) -> list[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT time, source, score
                FROM sentiment_stream
                WHERE symbol = $1
                  AND time >= NOW() - ($2 || ' minutes')::INTERVAL
                ORDER BY time DESC
                """,
                symbol,
                str(minutes),
            )
            return [dict(r) for r in rows]

    async def get_average(self, symbol: str, minutes: int = 60) -> float | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT AVG(score) AS avg_score
                FROM sentiment_stream
                WHERE symbol = $1
                  AND time >= NOW() - ($2 || ' minutes')::INTERVAL
                """,
                symbol,
                str(minutes),
            )
            return float(row["avg_score"]) if row and row["avg_score"] is not None else None
