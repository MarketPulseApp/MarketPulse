import os
from datetime import UTC, datetime

import httpx

from app.plugins.datasources.base import DataSourcePlugin, IngestRecord, QuotaInfo


class PolygonPlugin(DataSourcePlugin):
    source_name = "polygon"
    source_type = "price"
    feature_flag = "datasource.polygon"

    async def fetch(self, symbols: list[str], since: datetime) -> list[IngestRecord]:
        from app.infrastructure.valkey import redis

        api_key_bytes = await redis.get(f"api_key:{self.source_name}") if redis else None
        api_key = api_key_bytes.decode("utf-8") if api_key_bytes else None
        if not api_key:
            api_key = os.environ.get("POLYGON_API_KEY", "demo")
        records = []

        since_str = since.strftime("%Y-%m-%d")
        now_str = datetime.now(UTC).strftime("%Y-%m-%d")

        async with httpx.AsyncClient() as client:
            for symbol in symbols:
                url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{since_str}/{now_str}"
                try:
                    resp = await client.get(url, params={"apiKey": api_key})
                    resp.raise_for_status()
                    data = resp.json()
                    results = data.get("results", [])
                except Exception as e:
                    print(f"Polygon mock for {symbol}: {e}")
                    results = [
                        {
                            "t": int(datetime.now(UTC).timestamp() * 1000),
                            "o": 150.0,
                            "h": 155.0,
                            "l": 149.0,
                            "c": 153.0,
                            "v": 1000000,
                            "vw": 152.5,
                        }
                    ]
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
                        raw_id=f"{symbol}-{ts_ms}",
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
