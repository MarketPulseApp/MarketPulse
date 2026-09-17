from datetime import datetime

from app.plugins.datasources.base import DataSourcePlugin, IngestRecord, QuotaInfo


class RSSPlugin(DataSourcePlugin):
    source_name = "rss"
    source_type = "news"
    feature_flag = "datasource.rss"

    async def fetch(self, symbols: list[str], since: datetime) -> list[IngestRecord]:
        raise NotImplementedError("RSS plugin not yet implemented")

    def get_quota_info(self) -> QuotaInfo | None:
        return None
