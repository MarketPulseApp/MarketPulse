from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel


class PaperPortfolio(BaseModel):
    id: int
    cash: float
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class PaperTrade(BaseModel):
    id: int
    symbol: str
    action: str
    quantity: float
    price: float
    timestamp: datetime | None = None

    class Config:
        from_attributes = True


class PaperTradingRepository(ABC):
    @abstractmethod
    async def get_portfolio(self) -> PaperPortfolio | None:
        pass

    @abstractmethod
    async def get_trades(self, limit: int = 50) -> list[PaperTrade]:
        pass
