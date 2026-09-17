from datetime import datetime

import httpx
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.plugins.datasources.base import DataSourcePlugin, IngestRecord, QuotaInfo

analyzer = SentimentIntensityAnalyzer()


class BenzingaPlugin(DataSourcePlugin):
    source_name = "benzinga"
    source_type = "news"
    feature_flag = "datasource.benzinga"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    async def fetch(self, symbols: list[str], since: datetime) -> list[IngestRecord]:
        if not self.api_key:
            return []

        records = []
        async with httpx.AsyncClient() as client:
            # Benzinga allows comma separated symbols
            url = "https://api.benzinga.com/api/v2/news"
            params = {
                "token": self.api_key,
                "tickers": ",".join(symbols),
                "dateFrom": since.strftime("%Y-%m-%d"),
            }
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                for article in data:
                    text = f"{article.get('title', '')} {article.get('body', '')}"

                    # Synchronous VADER scoring during ingestion!
                    vader_score = analyzer.polarity_scores(text)

                    records.append(
                        IngestRecord(
                            source_name=self.source_name,
                            record_type="news",
                            ticker_symbols=[t.get("name") for t in article.get("stocks", [])],
                            timestamp=datetime.utcnow(),
                            payload={
                                "headline": article.get("title"),
                                "summary": article.get("body"),
                                "url": article.get("url"),
                                "vader_score": vader_score,
                            },
                            raw_id=str(article.get("id")),
                        )
                    )
            except Exception as e:
                import logging

                logging.getLogger(__name__).error(f"Benzinga failed: {e}")

        return records

    def get_quota_info(self) -> QuotaInfo:
        return QuotaInfo(
            source_name=self.source_name,
            daily_limit=500,
            monthly_limit=None,
            resets_at_midnight_utc=True,
        )
