from dataclasses import dataclass
from datetime import datetime


@dataclass
class Tick:
    symbol: str
    price: float
    volume: float
    timestamp: datetime


@dataclass
class OrderBookLevel:
    price: float
    volume: float


@dataclass
class OrderBook:
    symbol: str
    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]
    timestamp: datetime


@dataclass
class OHLCV:
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


from abc import ABC, abstractmethod


class MarketRepository(ABC):
    @abstractmethod
    async def get_latest_tick(self, symbol: str) -> Tick | None:
        pass

    @abstractmethod
    async def get_order_book(self, symbol: str) -> OrderBook | None:
        pass

    @abstractmethod
    async def get_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> list[OHLCV]:
        pass
