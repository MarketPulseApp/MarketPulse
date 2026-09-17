import logging
from datetime import UTC, datetime
from typing import Any

import feedparser
import httpx

from app.plugins.datasources.base import DataSourcePlugin, IngestRecord, QuotaInfo

logger = logging.getLogger(__name__)

class GenericRestAPIPlugin(DataSourcePlugin):
    """
    A generic plugin that can be instantiated dynamically by the UI
    given a URL, API token, and quota limit.
    """
    def __init__(
        self,
        source_name: str,
        record_type: str,
        base_url: str,
        api_token: str,
        daily_limit: int | None = None,
    ) -> None:
        self.source_name = source_name
        self.source_type = "rest_api"
        self.feature_flag = f"datasource.{source_name.lower().replace(' ', '_')}"
        self.record_type = record_type
        self.base_url = base_url
        self.api_token = api_token
        self._quota_info = QuotaInfo(
            source_name=self.source_name,
            daily_limit=daily_limit,
            monthly_limit=None,
            resets_at_midnight_utc=True
        )

    def get_quota_info(self) -> QuotaInfo | None:
        return self._quota_info

    async def fetch(self, symbols: list[str], since: datetime) -> list[IngestRecord]:
        logger.info(f"Fetching from generic REST API {self.source_name} for symbols: {symbols}")
        
        headers = {"Authorization": f"Bearer {self.api_token}"}
        records = []
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    self.base_url,
                    headers=headers,
                    params={"symbols": ",".join(symbols)}
                )
                response.raise_for_status()
                data = response.json()
                
                # Assume data is a list of dicts. In a real dynamic system, we'd need mapping rules.
                # For this generic implementation, we just store the raw payload.
                payload: dict[str, Any] = {"data": data} if isinstance(data, list) else data
                
                now_utc = datetime.now(UTC)
                records.append(
                    IngestRecord(
                        source_name=self.source_name,
                        record_type=self.record_type,
                        ticker_symbols=symbols,
                        timestamp=now_utc,
                        payload=payload,
                        raw_id=f"{self.source_name}_{now_utc.timestamp()}"
                    )
                )
            except httpx.HTTPError as e:
                logger.error(f"HTTP error fetching from {self.source_name}: {e}")
                raise
            except Exception as e:
                logger.error(f"Failed to fetch from {self.source_name}: {e}")
                raise
                
        return records


class GenericRSSPlugin(DataSourcePlugin):
    """
    A generic RSS feed plugin.
    """
    def __init__(self, source_name: str, feed_url: str) -> None:
        self.source_name = source_name
        self.source_type = "rss"
        self.feature_flag = f"datasource.{source_name.lower().replace(' ', '_')}"
        self.feed_url = feed_url

    def get_quota_info(self) -> QuotaInfo | None:
        return None  # RSS feeds rarely have quotas

    async def fetch(self, symbols: list[str], since: datetime) -> list[IngestRecord]:
        logger.info(f"Fetching from RSS feed {self.source_name}")
        
        records = []
        try:
            feed = feedparser.parse(self.feed_url)
            now_utc = datetime.now(UTC)
            for entry in feed.entries:
                # Basic check if it's newer than `since` could go here
                records.append(
                    IngestRecord(
                        source_name=self.source_name,
                        record_type="news",
                        ticker_symbols=symbols, # We would normally regex the text
                        timestamp=now_utc,
                        payload={
                            "title": getattr(entry, "title", ""),
                            "link": getattr(entry, "link", ""),
                            "summary": getattr(entry, "summary", "")
                        },
                        raw_id=getattr(entry, "id", getattr(entry, "link", str(now_utc.timestamp())))
                    )
                )
        except Exception as e:
            logger.error(f"Failed to fetch from RSS {self.source_name}: {e}")
            raise
            
        return records
