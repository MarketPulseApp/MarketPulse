from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from db.minio.model import ModelRepository


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.bucket_exists.return_value = True
    client.put_object = MagicMock()
    client.list_objects = MagicMock(return_value=iter([]))
    client.remove_object = MagicMock()

    response = MagicMock()
    response.read.return_value = b"model-bytes"
    response.close = MagicMock()
    response.release_conn = MagicMock()
    client.get_object = MagicMock(return_value=response)
    return client


@pytest.fixture
def repo(mock_client):
    return ModelRepository(mock_client)


@pytest.mark.asyncio
async def test_upload_puts_to_models_bucket(repo, mock_client):
    await repo.upload("AAPL", "lstm", "v1", b"model-data")
    assert mock_client.put_object.call_args[0][0] == "models"


@pytest.mark.asyncio
async def test_upload_key_structure(repo, mock_client):
    await repo.upload("AAPL", "lstm", "v1", b"data", ext="pkl")
    key = mock_client.put_object.call_args[0][1]
    assert key == "models/AAPL/lstm/v1.pkl"


@pytest.mark.asyncio
async def test_download_returns_bytes(repo, mock_client):
    result = await repo.download("AAPL", "lstm", "v1")
    assert result == b"model-bytes"
    mock_client.get_object.assert_called_once()


@pytest.mark.asyncio
async def test_download_releases_connection(repo, mock_client):
    await repo.download("AAPL", "lstm", "v1")
    response = mock_client.get_object.return_value
    response.close.assert_called_once()
    response.release_conn.assert_called_once()


@pytest.mark.asyncio
async def test_list_versions_empty(repo, mock_client):
    mock_client.list_objects.return_value = iter([])
    versions = await repo.list_versions("AAPL", "lstm")
    assert versions == []


@pytest.mark.asyncio
async def test_list_versions_returns_names(repo, mock_client):
    obj = MagicMock()
    obj.object_name = "models/AAPL/lstm/v1.pkl"
    mock_client.list_objects.return_value = iter([obj])
    versions = await repo.list_versions("AAPL", "lstm")
    assert versions == ["models/AAPL/lstm/v1.pkl"]


@pytest.mark.asyncio
async def test_delete_removes_object(repo, mock_client):
    await repo.delete("AAPL", "lstm", "v1")
    mock_client.remove_object.assert_called_once_with("models", "models/AAPL/lstm/v1.pkl")


def test_creates_bucket_if_not_exists():
    client = MagicMock()
    client.bucket_exists.return_value = False
    client.make_bucket = MagicMock()
    ModelRepository(client)
    client.make_bucket.assert_called_once_with("models")
