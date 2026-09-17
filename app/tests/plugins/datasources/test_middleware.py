from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.plugins.datasources.base import DataSourcePlugin, IngestRecord, QuotaInfo
from app.plugins.datasources.middleware import QuotaExceededException, QuotaMiddleware


class DummyPlugin(DataSourcePlugin):
    source_name = "dummy"
    source_type = "dummy_type"
    feature_flag = "dummy_flag"

    def __init__(self, limit=None):
        self.limit = limit
        self.call_count = 0

    async def fetch(self, symbols: list[str], since: datetime) -> list[IngestRecord]:
        self.call_count += 1
        return [
            IngestRecord(
                source_name=self.source_name,
                record_type="news",
                ticker_symbols=symbols,
                timestamp=datetime.now(UTC),
                payload={"data": "test"},
                raw_id=f"dummy_{self.call_count}",
            )
        ]

    def get_quota_info(self) -> QuotaInfo | None:
        if self.limit is None:
            return None
        return QuotaInfo(
            source_name=self.source_name,
            daily_limit=self.limit,
            monthly_limit=None,
            resets_at_midnight_utc=True,
        )


@pytest.fixture
def mock_redis():
    with patch("app.plugins.datasources.middleware.redis", new_callable=AsyncMock) as mock:
        yield mock


@pytest.mark.asyncio
async def test_quota_middleware_no_quota_info(mock_redis):
    """Test that plugins without quota info bypass quota checks completely."""
    plugin = DummyPlugin(limit=None)
    wrapped_plugin = QuotaMiddleware.wrap(plugin)

    records = await wrapped_plugin.fetch(["AAPL"], datetime.now(UTC))

    assert len(records) == 1
    assert plugin.call_count == 1
    mock_redis.get.assert_not_called()
    mock_redis.incrby.assert_not_called()


@pytest.mark.asyncio
async def test_quota_middleware_under_quota(mock_redis):
    """Test that execution proceeds and usage is incremented when under quota."""
    plugin = DummyPlugin(limit=10)
    wrapped_plugin = QuotaMiddleware.wrap(plugin)

    mock_redis.get.return_value = b"5"  # Simulate current usage of 5

    records = await wrapped_plugin.fetch(["AAPL"], datetime.now(UTC))

    assert len(records) == 1
    assert plugin.call_count == 1
    mock_redis.get.assert_called_once()
    mock_redis.incrby.assert_called_once()


@pytest.mark.asyncio
async def test_quota_middleware_over_quota(mock_redis):
    """Test that execution is blocked when quota is exceeded."""
    plugin = DummyPlugin(limit=10)
    wrapped_plugin = QuotaMiddleware.wrap(plugin)

    mock_redis.get.return_value = b"10"  # Simulate current usage at limit

    with pytest.raises(QuotaExceededException, match="Daily quota exceeded for dummy"):
        await wrapped_plugin.fetch(["AAPL"], datetime.now(UTC))

    assert plugin.call_count == 0
    mock_redis.get.assert_called_once()
    mock_redis.incrby.assert_not_called()


@pytest.mark.asyncio
async def test_quota_middleware_redis_none():
    """Test that the middleware gracefully degrades to allow requests if Redis is None."""
    with patch("app.plugins.datasources.middleware.redis", None):
        plugin = DummyPlugin(limit=10)
        wrapped_plugin = QuotaMiddleware.wrap(plugin)

        records = await wrapped_plugin.fetch(["AAPL"], datetime.now(UTC))

        assert len(records) == 1
        assert plugin.call_count == 1
