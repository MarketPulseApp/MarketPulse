import logging
from datetime import UTC, datetime

from app.infrastructure.valkey import redis
from app.plugins.datasources.base import DataSourcePlugin, IngestRecord

logger = logging.getLogger(__name__)

class QuotaExceededException(Exception):
    """Exception raised when API quotas are exceeded."""
    pass

class QuotaMiddleware:
    """
    Wraps DataSourcePlugin.fetch() to enforce API quotas tracked in Valkey (Redis).
    """

    @staticmethod
    async def get_daily_usage(source_name: str) -> int:
        if redis is None:
            return 0
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        key = f"quota:daily:{source_name}:{today}"
        try:
            val = await redis.get(key)
            return int(val) if val else 0
        except Exception as e:
            logger.error(f"Failed to read quota for {source_name}: {e}")
            return 0

    @staticmethod
    async def record_usage(source_name: str, count: int = 1) -> None:
        if redis is None:
            return
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        key = f"quota:daily:{source_name}:{today}"
        try:
            # Increment and set TTL to 48 hours to be safe
            await redis.incrby(key, count)
            await redis.expire(key, 48 * 3600)
        except Exception as e:
            logger.error(f"Failed to record quota usage for {source_name}: {e}")

    @staticmethod
    def wrap(plugin: DataSourcePlugin) -> DataSourcePlugin:
        original_fetch = plugin.fetch

        async def wrapped_fetch(symbols: list[str], since: datetime) -> list[IngestRecord]:
            quota_info = plugin.get_quota_info()

            if quota_info and quota_info.daily_limit:
                usage = await QuotaMiddleware.get_daily_usage(quota_info.source_name)
                if usage >= quota_info.daily_limit:
                    logger.warning(
                        f"Quota exceeded for {quota_info.source_name}. "
                        f"Limit: {quota_info.daily_limit}"
                    )
                    raise QuotaExceededException(
                        f"Daily quota exceeded for {quota_info.source_name}"
                    )

            # Make the actual fetch call
            try:
                if quota_info:
                    await QuotaMiddleware.record_usage(quota_info.source_name, 1)

                return await original_fetch(symbols, since)
            except Exception as e:
                logger.error(f"Error fetching from {plugin.source_name}: {e}")
                raise

        # Monkey patch the fetch method
        plugin.fetch = wrapped_fetch
        return plugin
