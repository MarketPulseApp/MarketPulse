from datetime import UTC, datetime

import pytest
import respx
from httpx import Response

from app.plugins.datasources.base import IngestRecord
from app.plugins.datasources.polygon_plugin import PolygonPlugin


@pytest.mark.asyncio
@respx.mock
async def test_polygon_plugin_fetch():
    plugin = PolygonPlugin()

    mock_payload = {
        "ticker": "AAPL",
        "results": [
            {
                "v": 1000,
                "vw": 150.5,
                "o": 150.0,
                "c": 151.0,
                "h": 152.0,
                "l": 149.0,
                "t": 1694822400000,
                "n": 100,
            }
        ],
    }

    # Mock Polygon API endpoint
    respx.get(url__regex=r"https://api\.polygon\.io/v2/aggs/ticker/.*").mock(
        return_value=Response(200, json=mock_payload)
    )

    records = await plugin.fetch(["AAPL"], datetime(2023, 9, 15, tzinfo=UTC))

    assert len(records) == 1
    record = records[0]

    # Verify mapping to IngestRecord
    assert isinstance(record, IngestRecord)
    assert record.source_name == "polygon"
    assert record.record_type == "price"
    assert "AAPL" in record.ticker_symbols
    assert record.timestamp == datetime.fromtimestamp(1694822400000 / 1000.0, tz=UTC)
    assert record.payload == mock_payload["results"][0]
    assert record.raw_id == "AAPL-1694822400000"
