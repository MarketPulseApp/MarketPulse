from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class IngestRecord:
    """Normalized output from any data source."""

    source_name: str
    record_type: str  # "news", "price", "sentiment", "onchain", "economic"
    ticker_symbols: list[str]
    timestamp: datetime
    payload: dict[str, Any]
    raw_id: str  # Source-specific unique ID for deduplication


@dataclass
class QuotaInfo:
    source_name: str
    daily_limit: int | None
    monthly_limit: int | None
    resets_at_midnight_utc: bool


class DataSourcePlugin(ABC):
    source_name: str
    source_type: str
    feature_flag: str

    @abstractmethod
    async def fetch(self, symbols: list[str], since: datetime) -> list[IngestRecord]:
        """Fetch new data for the given symbols since the given timestamp"""
        pass

    @abstractmethod
    def get_quota_info(self) -> QuotaInfo | None:
        """Return quota metadata, or None if this source has no quota tracking."""
        return None

    async def health_check(self) -> bool:
        """Returns True if source is reachable. Default: try a minimal fetch."""
        try:
            await self.fetch(["AAPL"], datetime.utcnow())
            return True
        except Exception:
            return False
