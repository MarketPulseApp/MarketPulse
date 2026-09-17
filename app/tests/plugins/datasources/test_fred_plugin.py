from datetime import UTC, datetime

import pytest
import respx
from httpx import Response

from app.plugins.datasources.base import IngestRecord
from app.plugins.datasources.fred_plugin import FREDPlugin


@pytest.mark.asyncio
@respx.mock
async def test_fred_plugin_fetch_yield_curve():
    plugin = FREDPlugin()

    # Mock 10Y Treasury (DGS10)
    respx.get(url__regex=r".*series_id=DGS10.*").mock(
        return_value=Response(200, json={"observations": [{"date": "2023-09-15", "value": "4.50"}]})
    )

    # Mock 2Y Treasury (DGS2)
    respx.get(url__regex=r".*series_id=DGS2.*").mock(
        return_value=Response(200, json={"observations": [{"date": "2023-09-15", "value": "5.00"}]})
    )

    records = await plugin.fetch(["YIELD_CURVE"], datetime(2023, 9, 14, tzinfo=UTC))

    assert len(records) == 1
    record = records[0]

    # Verify mapping to IngestRecord
    assert isinstance(record, IngestRecord)
    assert record.source_name == "fred"
    assert record.record_type == "economic"
    assert "YIELD_CURVE" in record.ticker_symbols
    assert record.timestamp == datetime(2023, 9, 15, tzinfo=UTC)

    # Verify yield curve slope computation (10Y - 2Y)
    assert record.payload["10y"] == 4.50
    assert record.payload["2y"] == 5.00
    assert record.payload["slope"] == -0.50
    assert record.raw_id == "YIELD_CURVE-2023-09-15"


@pytest.mark.asyncio
@respx.mock
async def test_fred_plugin_fetch_generic():
    plugin = FREDPlugin()

    # Mock Generic FRED series (e.g., GDP)
    respx.get(url__regex=r".*series_id=GDP.*").mock(
        return_value=Response(
            200, json={"observations": [{"date": "2023-09-15", "value": "26000.00"}]}
        )
    )

    records = await plugin.fetch(["GDP"], datetime(2023, 9, 14, tzinfo=UTC))

    assert len(records) == 1
    record = records[0]

    assert record.source_name == "fred"
    assert record.record_type == "economic"
    assert "GDP" in record.ticker_symbols
    assert record.timestamp == datetime(2023, 9, 15, tzinfo=UTC)
    assert record.payload["value"] == 26000.00
    assert record.raw_id == "GDP-2023-09-15"
