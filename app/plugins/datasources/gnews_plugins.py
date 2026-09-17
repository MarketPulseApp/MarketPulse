from datetime import datetime

from app.plugins.datasources.base import DataSourcePlugin, IngestRecord, QuotaInfo


class GNewsPlugin(DataSourcePlugin):
    source_name = "gnews"
    source_type = "news"
    feature_flag = "datasource.gnews"

    async def fetch(self, symbols: list[str], since: datetime) -> list[IngestRecord]:
        raise NotImplementedError("GNews plugin not yet implemented")

    def get_quota_info(self) -> QuotaInfo | None:
        return QuotaInfo(
            source_name="gnews",
            daily_limit=100,
            monthly_limit=None,
            resets_at_midnight_utc=True,
        )
