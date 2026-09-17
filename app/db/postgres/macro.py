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


class MacroRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def insert_macro(self, records: list[IngestRecord]) -> None:
        rows = []
        for record in records:
            for indicator, value in record.payload.items():
                if isinstance(value, (int, float)):
                    rows.append((record.timestamp, indicator, value))

        if not rows:
            return

        async with self.pool.acquire() as conn:
            await conn.executemany(
                "SELECT fn_insert_macro($1, $2, $3)",
                rows,
            )
