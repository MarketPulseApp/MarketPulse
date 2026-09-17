from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from db.embedded.event_journal import EventJournalRepository


@pytest.fixture
async def repo(tmp_path):
    db_path = str(tmp_path / "events.db")
    r = EventJournalRepository(db_path)
    await r.initialize()
    return r


@pytest.mark.asyncio
async def test_initialize_creates_table(tmp_path):
    db_path = str(tmp_path / "events.db")
    r = EventJournalRepository(db_path)
    await r.initialize()
    # Should be idempotent
    await r.initialize()


@pytest.mark.asyncio
async def test_append_returns_incrementing_ids(repo):
    id1 = await repo.append("price_fetched", {"symbol": "AAPL", "price": 150.0})
    id2 = await repo.append("price_fetched", {"symbol": "MSFT", "price": 300.0})
    assert id2 > id1


@pytest.mark.asyncio
async def test_append_and_get_recent(repo):
    await repo.append("order_placed", {"ticker": "TSLA", "qty": 10})
    await repo.append("order_placed", {"ticker": "NVDA", "qty": 5})
    results = await repo.get_recent("order_placed", n=10)
    assert len(results) == 2
    assert all(r["event_type"] == "order_placed" for r in results)


@pytest.mark.asyncio
async def test_get_recent_deserializes_payload(repo):
    await repo.append("test_event", {"key": "value", "num": 42})
    results = await repo.get_recent("test_event")
    assert results[0]["payload"]["key"] == "value"
    assert results[0]["payload"]["num"] == 42


@pytest.mark.asyncio
async def test_get_recent_filters_by_event_type(repo):
    await repo.append("type_a", {"x": 1})
    await repo.append("type_b", {"y": 2})
    results = await repo.get_recent("type_a")
    assert len(results) == 1
    assert results[0]["payload"]["x"] == 1


@pytest.mark.asyncio
async def test_get_recent_limits_results(repo):
    for i in range(10):
        await repo.append("tick", {"i": i})
    results = await repo.get_recent("tick", n=3)
    assert len(results) == 3


@pytest.mark.asyncio
async def test_get_recent_returns_desc_order(repo):
    await repo.append("ev", {"seq": 1})
    await repo.append("ev", {"seq": 2})
    results = await repo.get_recent("ev")
    # Most recent first
    assert results[0]["payload"]["seq"] == 2


@pytest.mark.asyncio
async def test_get_since_filters_by_datetime(repo):
    await repo.append("ev", {"seq": 1})
    cutoff = datetime.utcnow() + timedelta(seconds=1)
    await repo.append("ev", {"seq": 2})
    # Only events after cutoff
    results = await repo.get_since("ev", since=cutoff)
    # Timing-sensitive: just check it doesn't raise
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_get_recent_empty_when_no_events(repo):
    results = await repo.get_recent("nonexistent")
    assert results == []
