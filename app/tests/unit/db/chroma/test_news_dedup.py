from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from db.chroma.news_dedup import NewsDeduplicationRepository


@pytest.fixture
def mock_collection():
    col = AsyncMock()
    col.count = AsyncMock(return_value=10)
    return col


@pytest.fixture
def repo(mock_collection):
    client = AsyncMock()
    client.get_or_create_collection = AsyncMock(return_value=mock_collection)
    r = NewsDeduplicationRepository(client)
    r._collection = mock_collection
    return r


@pytest.mark.asyncio
async def test_is_duplicate_returns_false_when_empty(mock_collection):
    mock_collection.count = AsyncMock(return_value=0)
    client = AsyncMock()
    client.get_or_create_collection = AsyncMock(return_value=mock_collection)
    repo = NewsDeduplicationRepository(client)
    repo._collection = mock_collection

    result = await repo.is_duplicate([0.1, 0.2, 0.3])
    assert result is False
    mock_collection.query.assert_not_called()


@pytest.mark.asyncio
async def test_is_duplicate_true_when_close(repo, mock_collection):
    # distance=0.02 → similarity=0.98 → above default threshold 0.95 → duplicate
    mock_collection.query = AsyncMock(return_value={"distances": [[0.02]]})
    assert await repo.is_duplicate([0.1, 0.2]) is True


@pytest.mark.asyncio
async def test_is_duplicate_false_when_far(repo, mock_collection):
    # distance=0.2 → similarity=0.8 → below default threshold 0.95 → not duplicate
    mock_collection.query = AsyncMock(return_value={"distances": [[0.2]]})
    assert await repo.is_duplicate([0.1, 0.2]) is False


@pytest.mark.asyncio
async def test_is_duplicate_respects_custom_threshold(repo, mock_collection):
    mock_collection.query = AsyncMock(return_value={"distances": [[0.1]]})
    # threshold=0.85 → distance must be <= 0.15 → 0.1 qualifies
    assert await repo.is_duplicate([0.1], threshold=0.85) is True


@pytest.mark.asyncio
async def test_add_calls_collection_add(repo, mock_collection):
    mock_collection.add = AsyncMock()
    await repo.add("https://example.com", [0.1, 0.2], {"source": "reuters"})
    mock_collection.add.assert_awaited_once()
    call_kwargs = mock_collection.add.call_args.kwargs
    assert call_kwargs["ids"] == ["https://example.com"]
    assert call_kwargs["embeddings"] == [[0.1, 0.2]]
    assert call_kwargs["metadatas"] == [{"source": "reuters"}]


@pytest.mark.asyncio
async def test_lazy_collection_init():
    mock_col = AsyncMock()
    mock_col.count = AsyncMock(return_value=0)
    client = AsyncMock()
    client.get_or_create_collection = AsyncMock(return_value=mock_col)
    repo = NewsDeduplicationRepository(client)

    assert repo._collection is None
    await repo.is_duplicate([0.1])
    client.get_or_create_collection.assert_awaited_once_with(
        name="news_dedup", metadata={"hnsw:space": "cosine"}
    )
