from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from db.neo4j.ticker_graph import TickerGraphRepository


def make_driver(result_data=None):
    result_data = result_data or []
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=result_data)

    mock_session = AsyncMock()
    mock_session.run = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_driver = MagicMock()
    mock_driver.session = MagicMock(return_value=mock_session)
    return mock_driver, mock_session


@pytest.mark.asyncio
async def test_create_ticker_runs_merge(make_driver=make_driver):
    driver, session = make_driver()
    repo = TickerGraphRepository(driver)
    await repo.create_ticker("AAPL", "Apple Inc.")
    session.run.assert_awaited_once()
    cypher = session.run.call_args[0][0]
    assert "MERGE" in cypher
    assert "Ticker" in cypher


@pytest.mark.asyncio
async def test_add_sector_membership_merges_nodes():
    driver, session = make_driver()
    repo = TickerGraphRepository(driver)
    await repo.add_sector_membership("AAPL", "Technology")
    cypher = session.run.call_args[0][0]
    assert "Sector" in cypher
    assert "BELONGS_TO" in cypher


@pytest.mark.asyncio
async def test_add_correlation_upserts_edge():
    driver, session = make_driver()
    repo = TickerGraphRepository(driver)
    await repo.add_correlation("AAPL", "MSFT", r=0.85)
    cypher = session.run.call_args[0][0]
    assert "CORRELATED_WITH" in cypher
    assert "MERGE" in cypher


@pytest.mark.asyncio
async def test_get_peers_returns_symbols():
    driver, session = make_driver(
        result_data=[
            {"symbol": "MSFT"},
            {"symbol": "GOOGL"},
        ]
    )
    repo = TickerGraphRepository(driver)
    peers = await repo.get_peers("AAPL")
    assert peers == ["MSFT", "GOOGL"]


@pytest.mark.asyncio
async def test_get_peers_empty():
    driver, session = make_driver(result_data=[])
    repo = TickerGraphRepository(driver)
    peers = await repo.get_peers("AAPL")
    assert peers == []


@pytest.mark.asyncio
async def test_get_correlated_returns_dicts():
    driver, session = make_driver(
        result_data=[
            {"symbol": "MSFT", "r": 0.9, "window_days": 90},
        ]
    )
    repo = TickerGraphRepository(driver)
    results = await repo.get_correlated("AAPL", min_r=0.7)
    assert len(results) == 1
    assert results[0]["symbol"] == "MSFT"
    assert results[0]["r"] == 0.9


@pytest.mark.asyncio
async def test_deactivate_sets_is_active_false():
    driver, session = make_driver()
    repo = TickerGraphRepository(driver)
    await repo.deactivate("AAPL")
    cypher = session.run.call_args[0][0]
    assert "is_active" in cypher
    assert "false" in cypher.lower()
