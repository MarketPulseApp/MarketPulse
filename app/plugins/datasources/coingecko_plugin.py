from datetime import datetime

import httpx

from app.plugins.datasources.base import DataSourcePlugin, IngestRecord, QuotaInfo


class CoinGeckoPlugin(DataSourcePlugin):
    source_name = "coingecko"
    source_type = "onchain"
    feature_flag = "datasource.coingecko"

    async def fetch(self, symbols: list[str], since: datetime) -> list[IngestRecord]:
        records = []
        async with httpx.AsyncClient() as client:
            for symbol in symbols:
                # CoinGecko uses specific coin IDs, assuming symbol maps or is passed as ID for simplicity
                coin_id = symbol.lower().replace("-usd", "")
                url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
                params = {"vs_currency": "usd", "days": "1"}  # Since yesterday
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
                                payload={"market_data": data},
                                raw_id=f"coingecko_{symbol}_{since.timestamp()}",
                            )
                        )
                except Exception as e:
                    import logging

                    logging.getLogger(__name__).error(f"CoinGecko failed for {symbol}: {e}")

        return records

    def get_quota_info(self) -> QuotaInfo:
        return QuotaInfo(
            source_name=self.source_name,
            daily_limit=10000,  # CoinGecko free tier is usually generous or rate-limited per min
            monthly_limit=None,
            resets_at_midnight_utc=True,
        )
