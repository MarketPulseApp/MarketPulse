from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from db.neo4j.insider_graph import InsiderGraphRepository


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
async def test_add_person_uses_merge():
    driver, session = make_driver()
    repo = InsiderGraphRepository(driver)
    await repo.add_person("person-1", "Tim Cook", title="CEO")
    cypher = session.run.call_args[0][0]
    assert "MERGE" in cypher
    assert "Person" in cypher


@pytest.mark.asyncio
async def test_add_affiliation_links_person_to_ticker():
    driver, session = make_driver()
    repo = InsiderGraphRepository(driver)
    await repo.add_affiliation("person-1", "AAPL", role="CEO")
    cypher = session.run.call_args[0][0]
    assert "WORKS_AT" in cypher
    assert "MERGE" in cypher


@pytest.mark.asyncio
async def test_add_transaction_uses_create_not_merge():
    driver, session = make_driver()
    repo = InsiderGraphRepository(driver)
    await repo.add_transaction("person-1", "AAPL", "buy", shares=1000.0, price_per_share=150.0)
    cypher = session.run.call_args[0][0]
    assert "CREATE" in cypher
    assert "TRADED" in cypher
    # Ensure MERGE is not used for the relationship itself
    assert "MERGE (p)-[:TRADED" not in cypher


@pytest.mark.asyncio
async def test_get_insider_activity_returns_dicts():
    driver, session = make_driver(
        result_data=[
            {
                "name": "Tim Cook",
                "title": "CEO",
                "type": "buy",
                "shares": 1000.0,
                "price_per_share": 150.0,
                "filed_at": "2024-01-10",
            },
        ]
    )
    repo = InsiderGraphRepository(driver)
    results = await repo.get_insider_activity("AAPL")
    assert len(results) == 1
    assert results[0]["name"] == "Tim Cook"


@pytest.mark.asyncio
async def test_get_insider_activity_with_type_filter():
    driver, session = make_driver(result_data=[])
    repo = InsiderGraphRepository(driver)
    await repo.get_insider_activity("AAPL", transaction_type="sell")
    cypher = session.run.call_args[0][0]
    assert "rel.type = $transaction_type" in cypher


@pytest.mark.asyncio
async def test_get_insider_activity_no_type_filter():
    driver, session = make_driver(result_data=[])
    repo = InsiderGraphRepository(driver)
    await repo.get_insider_activity("AAPL")
    cypher = session.run.call_args[0][0]
    assert "rel.type = $transaction_type" not in cypher


@pytest.mark.asyncio
async def test_get_connected_insiders():
    driver, session = make_driver(
        result_data=[
            {"person_id": "p1", "name": "Shared Insider", "title": "Director"},
        ]
    )
    repo = InsiderGraphRepository(driver)
    results = await repo.get_connected_insiders("AAPL", "MSFT")
    assert len(results) == 1
    assert results[0]["name"] == "Shared Insider"
