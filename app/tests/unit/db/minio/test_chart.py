from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from db.minio.chart import ChartRepository


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.bucket_exists.return_value = True
    client.put_object = MagicMock()
    client.presigned_get_object = MagicMock(return_value="https://minio/presigned-url")
    client.list_objects = MagicMock(return_value=iter([]))
    return client


@pytest.fixture
def repo(mock_client):
    return ChartRepository(mock_client)


@pytest.mark.asyncio
async def test_upload_returns_presigned_url(repo, mock_client):
    url = await repo.upload("AAPL", b"fake-png-bytes")
    assert url == "https://minio/presigned-url"
    mock_client.put_object.assert_called_once()
    mock_client.presigned_get_object.assert_called_once()


@pytest.mark.asyncio
async def test_upload_puts_to_charts_bucket(repo, mock_client):
    await repo.upload("AAPL", b"png")
    call_args = mock_client.put_object.call_args
    assert call_args[0][0] == "charts"


@pytest.mark.asyncio
async def test_upload_key_contains_symbol(repo, mock_client):
    await repo.upload("TSLA", b"png")
    key = mock_client.put_object.call_args[0][1]
    assert "TSLA" in key


@pytest.mark.asyncio
async def test_upload_sets_content_type_png(repo, mock_client):
    await repo.upload("AAPL", b"png")
    kwargs = mock_client.put_object.call_args[1]
    assert kwargs.get("content_type") == "image/png"


@pytest.mark.asyncio
async def test_get_url_returns_presigned(repo, mock_client):
    url = await repo.get_url("charts/AAPL/2024-01-15.png")
    assert url == "https://minio/presigned-url"
    mock_client.presigned_get_object.assert_called_once()


@pytest.mark.asyncio
async def test_list_keys_empty_bucket(repo, mock_client):
    mock_client.list_objects.return_value = iter([])
    keys = await repo.list_keys("AAPL")
    assert keys == []


@pytest.mark.asyncio
async def test_list_keys_returns_object_names(repo, mock_client):
    obj1, obj2 = MagicMock(), MagicMock()
    obj1.object_name = "charts/AAPL/2024-01-15.png"
    obj2.object_name = "charts/AAPL/2024-01-16.png"
    mock_client.list_objects.return_value = iter([obj1, obj2])
    keys = await repo.list_keys("AAPL")
    assert len(keys) == 2
    assert all("AAPL" in k for k in keys)


def test_creates_bucket_if_not_exists():
    client = MagicMock()
    client.bucket_exists.return_value = False
    client.make_bucket = MagicMock()
    ChartRepository(client)
    client.make_bucket.assert_called_once_with("charts")
