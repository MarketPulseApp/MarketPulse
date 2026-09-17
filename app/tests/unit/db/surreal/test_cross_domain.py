from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from db.surreal.cross_domain import CrossDomainRepository


def surreal_result(data):
    return [{"result": data}]


@pytest.fixture
def client():
    return AsyncMock()


@pytest.fixture
def repo(client):
    return CrossDomainRepository(client)


@pytest.mark.asyncio
async def test_get_sector_news_calls_fn(repo, client):
    client.query = AsyncMock(return_value=surreal_result([{"headline": "Apple up"}]))
    await repo.get_sector_news("AAPL", days=7, sentiment_threshold=0.0)
    client.query.assert_awaited_once()
    query_str = client.query.call_args[0][0]
    assert "sector_news" in query_str


@pytest.mark.asyncio
async def test_get_sector_news_passes_params(repo, client):
    client.query = AsyncMock(return_value=surreal_result([]))
    await repo.get_sector_news("MSFT", days=14, sentiment_threshold=0.2)
    params = client.query.call_args[0][1]
    assert params["symbol"] == "MSFT"
    assert params["days"] == 14
    assert params["threshold"] == 0.2


@pytest.mark.asyncio
async def test_get_sector_news_returns_list(repo, client):
    articles = [{"headline": "A"}, {"headline": "B"}]
    client.query = AsyncMock(return_value=surreal_result(articles))
    results = await repo.get_sector_news("AAPL")
    assert results == articles


@pytest.mark.asyncio
async def test_get_sector_news_empty_result(repo, client):
    client.query = AsyncMock(return_value=surreal_result(None))
    results = await repo.get_sector_news("AAPL")
    assert results == []


@pytest.mark.asyncio
async def test_get_sector_news_no_result_key(repo, client):
    client.query = AsyncMock(return_value=[])
    results = await repo.get_sector_news("AAPL")
    assert results == []


@pytest.mark.asyncio
async def test_get_correlated_sentiment_calls_fn(repo, client):
    client.query = AsyncMock(return_value=surreal_result([]))
    await repo.get_correlated_sentiment("AAPL", days=30)
    query_str = client.query.call_args[0][0]
    # Check the function name is present (source may use single or double colon)
    assert "sector_sentiment" in query_str


@pytest.mark.asyncio
async def test_get_correlated_sentiment_passes_params(repo, client):
    client.query = AsyncMock(return_value=surreal_result([]))
    await repo.get_correlated_sentiment("TSLA", days=60)
    params = client.query.call_args[0][1]
    assert params["symbol"] == "TSLA"
    assert params["days"] == 60


@pytest.mark.asyncio
async def test_get_correlated_sentiment_returns_list(repo, client):
    data = [{"symbol": "MSFT", "avg_sentiment": 0.3, "article_count": 10}]
    client.query = AsyncMock(return_value=surreal_result(data))
    results = await repo.get_correlated_sentiment("AAPL")
    assert len(results) == 1
    assert results[0]["symbol"] == "MSFT"
