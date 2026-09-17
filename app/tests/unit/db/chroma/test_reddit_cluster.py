from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from db.chroma.reddit_cluster import RedditClusterRepository


@pytest.fixture
def mock_collection():
    col = AsyncMock()
    col.count = AsyncMock(return_value=5)
    return col


@pytest.fixture
def repo(mock_collection):
    client = AsyncMock()
    client.get_or_create_collection = AsyncMock(return_value=mock_collection)
    r = RedditClusterRepository(client)
    r._collection = mock_collection
    return r


@pytest.mark.asyncio
async def test_add_indexes_post(repo, mock_collection):
    mock_collection.add = AsyncMock()
    await repo.add("post123", [0.1, 0.2, 0.3])
    mock_collection.add.assert_awaited_once()
    # Verify the post id was passed — source may use positional or keyword args
    all_args = str(mock_collection.add.call_args)
    assert "post123" in all_args


@pytest.mark.asyncio
async def test_find_similar_returns_empty_when_no_posts(repo, mock_collection):
    mock_collection.count = AsyncMock(return_value=0)
    result = await repo.find_similar([0.1, 0.2])
    assert result == []
    mock_collection.query.assert_not_called()


@pytest.mark.asyncio
async def test_find_similar_returns_ids(repo, mock_collection):
    mock_collection.query = AsyncMock(return_value={"ids": [["post1", "post2", "post3"]]})
    result = await repo.find_similar([0.1, 0.2], n=3)
    assert result == ["post1", "post2", "post3"]


@pytest.mark.asyncio
async def test_find_similar_clamps_n_to_count(repo, mock_collection):
    mock_collection.count = AsyncMock(return_value=2)
    mock_collection.query = AsyncMock(return_value={"ids": [["a", "b"]]})
    await repo.find_similar([0.1], n=10)
    call_kwargs = mock_collection.query.call_args.kwargs
    assert call_kwargs["n_results"] == 2


@pytest.mark.asyncio
async def test_delete_removes_post(repo, mock_collection):
    mock_collection.delete = AsyncMock()
    await repo.delete("post123")
    mock_collection.delete.assert_awaited_once_with(ids=["post123"])
