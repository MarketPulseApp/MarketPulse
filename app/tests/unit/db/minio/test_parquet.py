from __future__ import annotations

import io
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from db.minio.parquet import ParquetRepository


def make_ohlcv_df():
    return pd.DataFrame(
        {
            "symbol": ["AAPL"],
            "open": [150.0],
            "high": [155.0],
            "low": [149.0],
            "close": [153.0],
            "volume": [1_000_000],
            "timestamp": ["2024-01-15 09:30:00"],
        }
    )


def df_to_parquet_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    return buf.getvalue()


def make_s3_no_such_key():
    """Create an S3Error that the source will catch as a missing key.

    The source checks: exc.code == "NoSuchKey"
    S3Error constructor signature varies by minio version, so we create
    a lightweight mock that mimics just what the source needs.
    """
    err = MagicMock()
    err.code = "NoSuchKey"
    # Make it behave like an exception when raised
    from minio.error import S3Error

    try:
        # Try the most common constructor signature
        return S3Error("NoSuchKey", "not found", "key", "req-id", "host-id", MagicMock())
    except TypeError:
        # Fallback: patch the code attribute on a generic exception
        e = Exception("NoSuchKey")
        e.code = "NoSuchKey"  # type: ignore[attr-defined]
        return e


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.bucket_exists.return_value = True
    client.put_object = MagicMock()
    return client


@pytest.fixture
def repo(mock_client):
    return ParquetRepository(mock_client)


@pytest.mark.asyncio
async def test_write_ohlcv_uploads_parquet(repo, mock_client):
    df = make_ohlcv_df()
    await repo.write_ohlcv("AAPL", date(2024, 1, 15), df)
    mock_client.put_object.assert_called_once()
    assert mock_client.put_object.call_args[0][0] == "parquet"


@pytest.mark.asyncio
async def test_write_ohlcv_key_contains_symbol_and_date(repo, mock_client):
    df = make_ohlcv_df()
    await repo.write_ohlcv("AAPL", date(2024, 1, 15), df)
    key = mock_client.put_object.call_args[0][1]
    assert "AAPL" in key
    assert "2024-01-15" in key


@pytest.mark.asyncio
async def test_read_ohlcv_empty_when_missing(repo, mock_client):
    from minio.error import S3Error

    class FakeS3Error(S3Error if hasattr(S3Error, "__mro__") else Exception):
        code = "NoSuchKey"

    # Patch the _get inner function to raise an error with code="NoSuchKey"

    def raise_no_such_key(*args, **kwargs):
        e = Exception("NoSuchKey")
        e.code = "NoSuchKey"  # type: ignore[attr-defined]
        raise type("S3Error", (Exception,), {"code": "NoSuchKey"})("NoSuchKey")

    mock_client.get_object = MagicMock(side_effect=raise_no_such_key)

    # Patch the S3Error check in the source to use our fake error type
    import db.minio.parquet as parquet_module

    class PatchedS3Error(Exception):
        def __init__(self, code="", *a, **kw):
            self.code = code
            super().__init__(code)

    with patch.object(parquet_module, "S3Error", PatchedS3Error):
        mock_client.get_object = MagicMock(side_effect=PatchedS3Error("NoSuchKey"))
        repo2 = ParquetRepository(mock_client)
        result = await repo2.read_ohlcv("AAPL", date(2024, 1, 15), date(2024, 1, 15))
    assert isinstance(result, pd.DataFrame)
    assert result.empty


@pytest.mark.asyncio
async def test_read_ohlcv_returns_dataframe(repo, mock_client):
    df = make_ohlcv_df()
    raw = df_to_parquet_bytes(df)

    response = MagicMock()
    response.read.return_value = raw
    response.close = MagicMock()
    response.release_conn = MagicMock()
    mock_client.get_object = MagicMock(return_value=response)

    result = await repo.read_ohlcv("AAPL", date(2024, 1, 15), date(2024, 1, 15))
    assert len(result) == 1
    assert result["close"].iloc[0] == pytest.approx(153.0)


@pytest.mark.asyncio
async def test_read_ohlcv_concatenates_multiple_days(repo, mock_client):
    df = make_ohlcv_df()
    raw = df_to_parquet_bytes(df)

    responses = []
    for _ in range(2):
        r = MagicMock()
        r.read.return_value = raw
        r.close = MagicMock()
        r.release_conn = MagicMock()
        responses.append(r)
    mock_client.get_object = MagicMock(side_effect=responses)

    result = await repo.read_ohlcv("AAPL", date(2024, 1, 15), date(2024, 1, 16))
    assert len(result) == 2


@pytest.mark.asyncio
async def test_read_ohlcv_skips_missing_dates(repo, mock_client):
    import db.minio.parquet as parquet_module

    class PatchedS3Error(Exception):
        def __init__(self, code="", *a, **kw):
            self.code = code
            super().__init__(code)

    df = make_ohlcv_df()
    raw = df_to_parquet_bytes(df)

    good_response = MagicMock()
    good_response.read.return_value = raw
    good_response.close = MagicMock()
    good_response.release_conn = MagicMock()

    with patch.object(parquet_module, "S3Error", PatchedS3Error):
        mock_client.get_object = MagicMock(side_effect=[PatchedS3Error("NoSuchKey"), good_response])
        repo2 = ParquetRepository(mock_client)
        result = await repo2.read_ohlcv("AAPL", date(2024, 1, 13), date(2024, 1, 14))
    assert len(result) == 1


def test_creates_bucket_if_not_exists():
    client = MagicMock()
    client.bucket_exists.return_value = False
    client.make_bucket = MagicMock()
    ParquetRepository(client)
    client.make_bucket.assert_called_once_with("parquet")
