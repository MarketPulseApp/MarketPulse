from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from db.chroma.feature_anomaly import FeatureAnomalyRepository


@pytest.fixture
def mock_collection():
    col = AsyncMock()
    col.count = AsyncMock(return_value=5)
    return col


@pytest.fixture
def repo(mock_collection):
    client = AsyncMock()
    client.get_or_create_collection = AsyncMock(return_value=mock_collection)
    r = FeatureAnomalyRepository(client)
    r._collection = mock_collection
    return r


@pytest.mark.asyncio
async def test_fit_adds_vectors(repo, mock_collection):
    mock_collection.delete = AsyncMock()
    mock_collection.add = AsyncMock()
    vectors = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
    await repo.fit(vectors)
    mock_collection.delete.assert_awaited_once()
    mock_collection.add.assert_awaited_once()
    add_kwargs = mock_collection.add.call_args.kwargs
    assert len(add_kwargs["ids"]) == 3
    assert add_kwargs["embeddings"] == vectors


@pytest.mark.asyncio
async def test_fit_clears_old_baseline(repo, mock_collection):
    mock_collection.delete = AsyncMock()
    mock_collection.add = AsyncMock()
    await repo.fit([[0.1, 0.2]])
    delete_kwargs = mock_collection.delete.call_args.kwargs
    assert delete_kwargs["where"] == {"source": "baseline"}


@pytest.mark.asyncio
async def test_fit_tolerates_empty_delete(repo, mock_collection):
    mock_collection.delete = AsyncMock(side_effect=Exception("empty"))
    mock_collection.add = AsyncMock()
    await repo.fit([[0.1]])  # should not raise
    mock_collection.add.assert_awaited_once()


@pytest.mark.asyncio
async def test_score_returns_zero_when_empty(repo, mock_collection):
    mock_collection.count = AsyncMock(return_value=0)
    result = await repo.score([0.1, 0.2])
    assert result == 0.0
    mock_collection.query.assert_not_called()


@pytest.mark.asyncio
async def test_score_returns_distance(repo, mock_collection):
    mock_collection.query = AsyncMock(return_value={"distances": [[0.42]]})
    result = await repo.score([0.1, 0.2])
    assert result == pytest.approx(0.42)


@pytest.mark.asyncio
async def test_score_queries_nearest_one(repo, mock_collection):
    mock_collection.query = AsyncMock(return_value={"distances": [[0.1]]})
    await repo.score([0.5, 0.5])
    call_kwargs = mock_collection.query.call_args.kwargs
    assert call_kwargs["n_results"] == 1
