from datetime import datetime

import httpx
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from app.plugins.datasources.base import DataSourcePlugin, IngestRecord, QuotaInfo

analyzer = SentimentIntensityAnalyzer()


class NewsAPIPlugin(DataSourcePlugin):
    source_name = "newsapi"
    source_type = "news"
    feature_flag = "datasource.newsapi"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    async def fetch(self, symbols: list[str], since: datetime) -> list[IngestRecord]:
        if not self.api_key:
            return []

        records = []
        async with httpx.AsyncClient() as client:
            for symbol in symbols:
                url = f"https://newsapi.org/v2/everything?q={symbol}&from={since.strftime('%Y-%m-%d')}&sortBy=publishedAt&apiKey={self.api_key}"
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    data = response.json()

                    for article in data.get("articles", []):
                        text = f"{article.get('title', '')} {article.get('description', '')}"

                        # Synchronous VADER scoring during ingestion!
                        vader_score = analyzer.polarity_scores(text)

                        records.append(
                            IngestRecord(
                                source_name=self.source_name,
                                record_type="news",
                                ticker_symbols=[symbol],
                                timestamp=datetime.utcnow(),  # Needs proper parsing
                                payload={
                                    "headline": article.get("title"),
                                    "summary": article.get("description"),
                                    "url": article.get("url"),
                                    "vader_score": vader_score,
                                },
                                raw_id=article.get("url"),
                            )
                        )
                except Exception as e:
                    import logging

                    logging.getLogger(__name__).error(f"NewsAPI failed for {symbol}: {e}")

        return records

    def get_quota_info(self) -> QuotaInfo:
        return QuotaInfo(
            source_name=self.source_name,
            daily_limit=100,  # Developer tier limit
            monthly_limit=None,
            resets_at_midnight_utc=True,
        )
