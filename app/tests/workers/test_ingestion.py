from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workers.ingestion import cron_poll_all_sources, run_ingestion_for_plugin


class MockRecord:
    def __init__(self, record_type="news", **kwargs):
        self.record_type = record_type
        for k, v in kwargs.items():
            setattr(self, k, v)


@pytest.fixture
def mock_ctx():
    return {"redis": AsyncMock()}


@pytest.fixture
def mock_plugin():
    plugin = MagicMock()
    plugin.source_name = "test_source"
    plugin.fetch = AsyncMock()
    return plugin


@pytest.mark.asyncio
@patch("app.workers.ingestion.get_enabled_datasources")
async def test_cron_poll_all_sources(mock_get_plugins, mock_ctx, mock_plugin):
    mock_get_plugins.return_value = [mock_plugin]

    await cron_poll_all_sources(mock_ctx)

    mock_ctx["redis"].enqueue_job.assert_called_once()
    args, kwargs = mock_ctx["redis"].enqueue_job.call_args
    assert args[0] == "run_ingestion_for_plugin"
    assert kwargs["source_name"] == "test_source"
    assert "symbols" in kwargs
    assert "since" in kwargs


@pytest.mark.asyncio
@patch("app.workers.ingestion.get_enabled_datasources")
async def test_run_ingestion_for_plugin_news(mock_get_plugins, mock_ctx, mock_plugin):
    mock_get_plugins.return_value = [mock_plugin]

    # Use a dummy object so __dict__ extraction works as expected
    mock_record = MockRecord(
        record_type="news", payload={"summary": "test"}, ticker_symbols=["AAPL"]
    )
    mock_plugin.fetch.return_value = [mock_record]

    since = datetime.now(UTC)
    await run_ingestion_for_plugin(mock_ctx, "test_source", ["AAPL"], since)

    mock_ctx["redis"].enqueue_job.assert_called_once_with(
        "deduplicate_and_store_news", records=[mock_record.__dict__]
    )


@pytest.mark.asyncio
@patch("app.workers.ingestion.get_enabled_datasources")
async def test_run_ingestion_for_plugin_no_records(mock_get_plugins, mock_ctx, mock_plugin):
    mock_get_plugins.return_value = [mock_plugin]
    mock_plugin.fetch.return_value = []

    since = datetime.now(UTC)
    await run_ingestion_for_plugin(mock_ctx, "test_source", ["AAPL"], since)

    mock_ctx["redis"].enqueue_job.assert_not_called()


@pytest.mark.asyncio
@patch("app.workers.ingestion.get_enabled_datasources")
async def test_run_ingestion_for_plugin_not_found(mock_get_plugins, mock_ctx):
    mock_get_plugins.return_value = []

    since = datetime.now(UTC)
    await run_ingestion_for_plugin(mock_ctx, "missing_source", ["AAPL"], since)

    mock_ctx["redis"].enqueue_job.assert_not_called()
