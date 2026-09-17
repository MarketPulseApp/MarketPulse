from datetime import datetime

import asyncpg

from app.core.config import settings
from app.plugins.datasources.base import IngestRecord


# TODO: Remove in Phase 5
async def create_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=settings.POSTGRES_DATABASE,
    )


class OHLCVRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def insert_batch(self, records: list[IngestRecord]) -> None:
        rows = [
            (
                record.timestamp,
                record.ticker_symbols[0],
                record.payload["open"],
                record.payload["high"],
                record.payload["low"],
                record.payload["close"],
                record.payload["volume"],
            )
            for record in records
        ]
        async with self.pool.acquire() as conn:
            await conn.executemany(
                "SELECT fn_insert_ohlcv($1, $2, $3, $4, $5, $6, $7)",
                rows,
            )

    async def get_recent(self, symbol: str, days: int) -> list[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM fn_get_ohlcv_recent($1, $2)", symbol, days)
            return [dict(row) for row in rows]

    async def get_range(self, symbol: str, start: datetime, end: datetime) -> list[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * from fn_get_ohlcv_range($1, $2, $3)", symbol, start, end
            )
            return [dict(row) for row in rows]
