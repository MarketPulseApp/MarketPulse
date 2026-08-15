from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class Ticker:
    symbol: str = ""
    name: str = ""
    asset_type: Literal["stock", "crypto", "etf", "index"] = "stock"
    sector: str | None = None
    industry: str | None = None
    market_cap: int | None = None
    logo_url: str | None = None
    is_active: bool = True
    added_at: datetime | None = None
    subreddits: list[str] = field(default_factory=list)

    def is_stock(self):
        return self.asset_type == "stock"

    def is_crypto(self):
        return self.asset_type == "crypto"

    def get_display_name(self):
        return self.name


@dataclass
class StockTicker(Ticker):
    exchange: str | None = None


@dataclass
class CryptoTicker(Ticker):
    chain: str | None = None
    coingecko_id: str | None = None


@dataclass
class IndexTicker(Ticker):
    pass
