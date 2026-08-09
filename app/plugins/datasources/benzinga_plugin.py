from datetime import datetime

from app.plugins.datasources.base import DataSourcePlugin, IngestRecord, QuotaInfo


class BenzingaPlugin(DataSourcePlugin):
    source_name = "bezinga"
    source_type = "news"
    feature_flag = "datasource.bezinga"

    async def fetch(self, symbols: list[str], since: datetime) -> list[IngestRecord]:
        # Fetch from Benzinga API
        articles = await benzinga_client.get_news(symbols=symbols, since=since)  # noqa: F821
        return [
            IngestRecord(
                source_name=self.source_name,
                record_type="news",
                ticker_symbols=[a.ticker],
                timestamp=a.published_at,
                payload={"headline": a.title, "summary": a.summary, "url": a.url},
                raw_id=a.id,
            )
            for a in articles
        ]

    def get_quota_info(self) -> QuotaInfo:
        return QuotaInfo(
            source_name="benzinga",
            daily_limit=500,
            monthly_limit=None,
            resets_at_midnight_utc=True,
        )
