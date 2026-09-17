import asyncpg

from app.core.config import settings
from app.domain.ticker import Ticker


# TODO: Remove in Phase 5
async def create_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=settings.POSTGRES_DATABASE,
    )


class TickerRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def get_all_active(self) -> list[Ticker]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM fn_get_all_active_tickers()")
            return [
                Ticker(
                    symbol=row["symbol"],
                    name=row["name"],
                    sector=row["sector"],
                    asset_type=row["asset_type"],
                    is_active=bool(row["is_active"]),
                    added_at=row["created_at"],
                )
                for row in rows
            ]

    async def insert(self, ticker: Ticker) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "SELECT fn_insert_ticker($1, $2, $3, $4, $5, $6, $7)",
                ticker.symbol,
                ticker.name,
                ticker.asset_type,
                ticker.sector,
                getattr(ticker, "exchange", None),
                ticker.currency,
                ticker.is_active,
            )

    async def deactivate(self, symbol: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("SELECT fn_deactivate_ticker($1)", symbol)
