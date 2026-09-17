from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from app.plugins.datasources.base import IngestRecord
from app.plugins.datasources.sec_edgar_plugin import SECEdgarPlugin
from app.plugins.datasources.yfinance_plugin import YFinancePlugin


@pytest.fixture
def sec_plugin():
    return SECEdgarPlugin()


@pytest.fixture
def yf_plugin():
    return YFinancePlugin()


@pytest.mark.asyncio
@patch("app.plugins.datasources.sec_edgar_plugin.httpx.AsyncClient")
async def test_sec_edgar_plugin_form4_normal(mock_client, sec_plugin):
    """Test SEC Edgar plugin processes normal Form 4 data correctly."""
    mock_get = AsyncMock()
    mock_client.return_value.__aenter__.return_value.get = mock_get

    # Mocking SEC Edgar JSON response for a normal Form 4
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "filings": [
            {
                "accessionNumber": "0001234567-89-000001",
                "filingDate": "2023-10-01",
                "reportDate": "2023-09-30",
                "form": "4",
                "issuer": {"tradingSymbol": "AAPL"},
                "transactions": [
                    {
                        "transactionDate": "2023-09-30",
                        "transactionCode": "P",  # Purchase
                        "shares": 1000,
                        "pricePerShare": 150.0,
                    }
                ],
            }
        ]
    }
    mock_get.return_value = mock_response

    since_time = datetime(2023, 9, 1, tzinfo=UTC)
    records = await sec_plugin.fetch(["AAPL"], since=since_time)

    assert len(records) > 0
    record = records[0]
    assert isinstance(record, IngestRecord)
    assert record.source_name == "sec_edgar"
    assert record.record_type == "news"  # or whatever the plugin uses
    assert "AAPL" in record.ticker_symbols
    assert record.raw_id == "0001234567-89-000001"
    assert record.payload["form"] == "4"
    assert record.payload["transactions"][0]["transactionCode"] == "P"


@pytest.mark.asyncio
@patch("app.plugins.datasources.sec_edgar_plugin.httpx.AsyncClient")
async def test_sec_edgar_plugin_form4_strange_type(mock_client, sec_plugin):
    """Test SEC Edgar plugin handles strange Form 4 transaction types."""
    mock_get = AsyncMock()
    mock_client.return_value.__aenter__.return_value.get = mock_get

    # Mocking SEC Edgar JSON response for a strange Form 4 transaction type
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "filings": [
            {
                "accessionNumber": "0001234567-89-000002",
                "filingDate": "2023-10-02",
                "reportDate": "2023-10-01",
                "form": "4",
                "issuer": {"tradingSymbol": "TSLA"},
                "transactions": [
                    {
                        "transactionDate": "2023-10-01",
                        "transactionCode": "Z",  # Strange/Unknown type
                        "shares": 500,
                        "pricePerShare": 250.0,
                    }
                ],
            }
        ]
    }
    mock_get.return_value = mock_response

    since_time = datetime(2023, 9, 1, tzinfo=UTC)
    records = await sec_plugin.fetch(["TSLA"], since=since_time)

    assert len(records) > 0
    record = records[0]
    assert record.raw_id == "0001234567-89-000002"
    assert record.payload["transactions"][0]["transactionCode"] == "Z"


@pytest.mark.asyncio
@patch("app.plugins.datasources.yfinance_plugin.yf.Ticker")
async def test_yfinance_plugin_normal(mock_ticker_class, yf_plugin):
    """Test YFinance plugin processes price data and EPS estimates normally."""
    mock_ticker = MagicMock()
    mock_ticker_class.return_value = mock_ticker

    # Mock history dataframe
    df = pd.DataFrame(
        {"Open": [150.0], "High": [155.0], "Low": [149.0], "Close": [154.0], "Volume": [1000000]},
        index=[pd.Timestamp("2023-10-01", tz="UTC")],
    )
    mock_ticker.history.return_value = df

    # Mock info dictionary with EPS
    mock_ticker.info = {"trailingEps": 5.5, "forwardEps": 6.0}

    since_time = datetime(2023, 9, 1, tzinfo=UTC)
    records = await yf_plugin.fetch(["AAPL"], since=since_time)

    assert len(records) > 0
    record = records[0]
    assert isinstance(record, IngestRecord)
    assert record.source_name == "yfinance"
    assert record.record_type == "price"
    assert "AAPL" in record.ticker_symbols
    assert record.payload["Open"] == 150.0
    assert record.payload["trailingEps"] == 5.5


@pytest.mark.asyncio
@patch("app.plugins.datasources.yfinance_plugin.yf.Ticker")
async def test_yfinance_plugin_missing_eps(mock_ticker_class, yf_plugin):
    """Test YFinance plugin handles missing EPS estimates gracefully."""
    mock_ticker = MagicMock()
    mock_ticker_class.return_value = mock_ticker

    # Mock history dataframe
    df = pd.DataFrame(
        {"Open": [150.0], "High": [155.0], "Low": [149.0], "Close": [154.0], "Volume": [1000000]},
        index=[pd.Timestamp("2023-10-01", tz="UTC")],
    )
    mock_ticker.history.return_value = df

    # Mock info dictionary with missing EPS (NaN or completely missing)
    mock_ticker.info = {
        "trailingEps": np.nan,  # Simulate missing EPS
        # "forwardEps" missing entirely
    }

    since_time = datetime(2023, 9, 1, tzinfo=UTC)
    records = await yf_plugin.fetch(["AAPL"], since=since_time)

    assert len(records) > 0
    record = records[0]
    assert record.source_name == "yfinance"

    # Check that missing EPS is handled (e.g., set to None or preserved as NaN without crashing)
    # The exact assertion might depend on implementation, but we assert it doesn't crash and maps payload
    assert "Open" in record.payload
    # Depending on implementation, NaN might be converted to None for JSON serialization
    assert np.isnan(record.payload.get("trailingEps")) or record.payload.get("trailingEps") is None
    assert record.payload.get("forwardEps") is None
