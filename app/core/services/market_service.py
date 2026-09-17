from app.domain.market import OHLCV, MarketRepository, OrderBook, Tick


class MarketService:
    def __init__(self, market_repo: MarketRepository):
        self.market_repo = market_repo

    async def get_latest_tick(self, symbol: str) -> Tick | None:
        return await self.market_repo.get_latest_tick(symbol)

    async def get_order_book(self, symbol: str) -> OrderBook | None:
        return await self.market_repo.get_order_book(symbol)

    async def get_ohlcv(self, symbol: str, timeframe: str = "1d", limit: int = 100) -> list[OHLCV]:
        return await self.market_repo.get_ohlcv(symbol, timeframe, limit)
