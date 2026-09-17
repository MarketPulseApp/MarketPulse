from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from db.surreal.sector import SectorRepository


def surreal_result(data):
    return [{"result": data}]


@pytest.fixture
def client():
    return AsyncMock()


@pytest.fixture
def repo(client):
    return SectorRepository(client)


@pytest.mark.asyncio
async def test_get_peers_calls_fn(repo, client):
    client.query = AsyncMock(return_value=surreal_result([{"symbol": "MSFT"}]))
    await repo.get_peers("AAPL")
    query_str = client.query.call_args[0][0]
    assert "fn::sector_peers" in query_str


@pytest.mark.asyncio
async def test_get_peers_returns_symbol_list(repo, client):
    client.query = AsyncMock(
        return_value=surreal_result(
            [
                {"symbol": "MSFT"},
                {"symbol": "GOOGL"},
            ]
        )
    )
    peers = await repo.get_peers("AAPL")
    assert peers == ["MSFT", "GOOGL"]


@pytest.mark.asyncio
async def test_get_peers_empty(repo, client):
    client.query = AsyncMock(return_value=surreal_result(None))
    peers = await repo.get_peers("AAPL")
    assert peers == []


@pytest.mark.asyncio
async def test_upsert_ticker_calls_fn(repo, client):
    client.query = AsyncMock(return_value=surreal_result(None))
    await repo.upsert_ticker("AAPL", "Technology", "Apple Inc.")
    query_str = client.query.call_args[0][0]
    assert "fn::upsert_ticker" in query_str


@pytest.mark.asyncio
async def test_upsert_ticker_passes_params(repo, client):
    client.query = AsyncMock(return_value=surreal_result(None))
    await repo.upsert_ticker("TSLA", "Consumer Cyclical", "Tesla Inc.")
    params = client.query.call_args[0][1]
    assert params["symbol"] == "TSLA"
    assert params["sector"] == "Consumer Cyclical"
    assert params["name"] == "Tesla Inc."


@pytest.mark.asyncio
async def test_get_all_sectors_returns_list(repo, client):
    client.query = AsyncMock(return_value=surreal_result(["Technology", "Healthcare"]))
    sectors = await repo.get_all_sectors()
    assert sectors == ["Technology", "Healthcare"]


@pytest.mark.asyncio
async def test_get_all_sectors_empty(repo, client):
    client.query = AsyncMock(return_value=surreal_result(None))
    sectors = await repo.get_all_sectors()
    assert sectors == []
