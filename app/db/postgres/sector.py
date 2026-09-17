from __future__ import annotations

import asyncpg


class SectorRepository:
    """Sector and cross-domain queries via PostgreSQL — replaces SurrealDB."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def get_peers(self, symbol: str) -> list[str]:
        """Return active tickers in the same sector as *symbol*."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT t2.symbol
                FROM tickers t1
                JOIN tickers t2 ON t1.sector = t2.sector
                WHERE t1.symbol = $1
                  AND t2.symbol <> $1
                  AND t2.is_active = true
                """,
                symbol,
            )
            return [row["symbol"] for row in rows]

    async def upsert_ticker(self, symbol: str, sector: str, name: str) -> None:
        """Create or update a ticker record."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "SELECT fn_insert_ticker($1, $2, 'stock', $3, NULL, 'USD', true)",
                symbol,
                name,
                sector,
            )

    async def get_all_sectors(self) -> list[str]:
        """Return a deduplicated, sorted list of all sectors."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT DISTINCT sector FROM tickers WHERE sector IS NOT NULL ORDER BY sector"
            )
            return [row["sector"] for row in rows]

    async def get_sector_sentiment(
        self,
        symbol: str,
        days: int = 7,
        sentiment_threshold: float = 0.0,
    ) -> list[dict]:
        """Return sentiment scores for every peer ticker in the same sector."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT s.symbol, s.score, s.recorded_at, s.source_name
                FROM sentiment_daily s
                JOIN tickers t1 ON s.symbol = t1.symbol
                JOIN tickers t2 ON t1.sector = t2.sector
                WHERE t2.symbol = $1
                  AND s.recorded_at >= NOW() - ($2 * INTERVAL '1 day')
                  AND s.score >= $3
                ORDER BY s.recorded_at DESC
                """,
                symbol,
                days,
                sentiment_threshold,
            )
            return [dict(row) for row in rows]

    async def get_correlated_sentiment(self, symbol: str, days: int = 30) -> list[dict]:
        """Return average sentiment grouped by peer ticker over *days*."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT t2.symbol, AVG(s.score) AS avg_sentiment
                FROM sentiment_daily s
                JOIN tickers t1 ON s.symbol = t1.symbol
                JOIN tickers t2 ON t1.sector = t2.sector
                WHERE t2.symbol = $1
                  AND s.recorded_at >= NOW() - ($2 * INTERVAL '1 day')
                GROUP BY t2.symbol
                ORDER BY t2.symbol
                """,
                symbol,
                days,
            )
            return [dict(row) for row in rows]
