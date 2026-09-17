import os
from datetime import UTC, datetime

import httpx

from app.plugins.datasources.base import DataSourcePlugin, IngestRecord, QuotaInfo


class PolygonPlugin(DataSourcePlugin):
    source_name = "polygon"
    source_type = "price"
    feature_flag = "datasource.polygon"

    async def fetch(self, symbols: list[str], since: datetime) -> list[IngestRecord]:
        api_key = os.environ.get("POLYGON_API_KEY", "demo")
        records = []
        
        since_str = since.strftime("%Y-%m-%d")
        now_str = datetime.now(UTC).strftime("%Y-%m-%d")
        
        async with httpx.AsyncClient() as client:
            for symbol in symbols:
                url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{since_str}/{now_str}"
                resp = await client.get(url, params={"apiKey": api_key})
                resp.raise_for_status()
                data = resp.json()
                
                results = data.get("results", [])
                for res in results:
                    ts_ms = res.get("t")
                    if not ts_ms:
                        continue
                    dt = datetime.fromtimestamp(ts_ms / 1000.0, tz=UTC)
                    record = IngestRecord(
                        source_name=self.source_name,
                        record_type=self.source_type,
                        ticker_symbols=[symbol],
                        timestamp=dt,
                        payload=res,
                        raw_id=f"{symbol}-{ts_ms}"
                    )
                    records.append(record)
                    
        return records

    def get_quota_info(self) -> QuotaInfo | None:
        return QuotaInfo(
            source_name="polygon",
            daily_limit=None,
            monthly_limit=None,
            resets_at_midnight_utc=False,
        )
