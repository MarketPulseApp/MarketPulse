
import asyncpg

from app.domain.paper_trading import PaperPortfolio, PaperTrade, PaperTradingRepository


class PaperTradingRepositoryImpl(PaperTradingRepository):
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def get_portfolio(self) -> PaperPortfolio | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, cash, updated_at FROM paper_portfolio ORDER BY id DESC LIMIT 1"
            )
            if row:
                return PaperPortfolio(
                    id=row["id"],
                    cash=row["cash"],
                    updated_at=row["updated_at"]
                )
            return None

    async def get_trades(self, limit: int = 50) -> list[PaperTrade]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, symbol, action, quantity, price, timestamp FROM paper_trades ORDER BY timestamp DESC, id DESC LIMIT $1",
                limit
            )
            return [
                PaperTrade(
                    id=row["id"],
                    symbol=row["symbol"],
                    action=row["action"],
                    quantity=row["quantity"],
                    price=row["price"],
                    timestamp=row["timestamp"]
                )
                for row in rows
            ]
