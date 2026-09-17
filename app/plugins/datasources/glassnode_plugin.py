from datetime import datetime

import httpx

from app.plugins.datasources.base import DataSourcePlugin, IngestRecord, QuotaInfo


class GlassnodePlugin(DataSourcePlugin):
    source_name = "glassnode"
    source_type = "onchain"
    feature_flag = "datasource.glassnode"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    async def fetch(self, symbols: list[str], since: datetime) -> list[IngestRecord]:
        if not self.api_key:
            return []

        records = []
        async with httpx.AsyncClient() as client:
            for symbol in symbols:
                # Basic metric: active addresses
                url = "https://api.glassnode.com/v1/metrics/addresses/active_count"
                params = {
                    "a": symbol.replace("-USD", ""),  # Map standard crypto tickers
                    "api_key": self.api_key,
                    "s": int(since.timestamp()),
                }
                try:
                    response = await client.get(url, params=params)
                    if response.status_code == 200:
                        data = response.json()
                        records.append(
                            IngestRecord(
                                source_name=self.source_name,
                                record_type="onchain",
                                ticker_symbols=[symbol],
                                timestamp=datetime.utcnow(),
                                payload={"active_addresses": data},
                                raw_id=f"glassnode_addr_{symbol}_{since.timestamp()}",
                            )
                        )
                except Exception as e:
                    import logging

                    logging.getLogger(__name__).error(f"Glassnode failed for {symbol}: {e}")

        return records

    def get_quota_info(self) -> QuotaInfo:
        return QuotaInfo(
            source_name=self.source_name,
            daily_limit=1000,
            monthly_limit=None,
            resets_at_midnight_utc=True,
        )
