from app.domain.paper_trading import PaperPortfolio, PaperTrade, PaperTradingRepository


class PaperTradingService:
    def __init__(self, repository: PaperTradingRepository):
        self.repository = repository

    async def get_portfolio(self) -> PaperPortfolio | None:
        return await self.repository.get_portfolio()

    async def get_trades(self, limit: int = 50) -> list[PaperTrade]:
        return await self.repository.get_trades(limit=limit)
