from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from db.influx.mention_count import MentionCountRepository


class MockRecord:
    def __init__(self, time, values):
        self._time = time
        self.values = values

    def get_time(self):
        return self._time

    def get_value(self):
        return self.values.get("count", 0)


class MockTable:
    def __init__(self, records):
        self.records = records


@pytest.fixture
def client():
    # write_api() and query_api() are called as regular (sync) methods in the source,
    # so the client itself must be a MagicMock, not AsyncMock.
    c = MagicMock()

    write_api = AsyncMock()
    write_api.__aenter__ = AsyncMock(return_value=write_api)
    write_api.__aexit__ = AsyncMock(return_value=False)
    write_api.write = AsyncMock()
    c.write_api.return_value = write_api

    query_api = MagicMock()
    query_api.query = AsyncMock(return_value=[])
    c.query_api.return_value = query_api

    return c


@pytest.fixture
def repo(client):
    return MentionCountRepository(client, org="marketpulse")


@pytest.mark.asyncio
async def test_write_creates_point_with_tags(repo, client):
    write_api = client.write_api.return_value
    await repo.write("AAPL", "wallstreetbets", count=10, avg_score=0.5)
    write_api.write.assert_awaited_once()
    call_kwargs = write_api.write.call_args.kwargs
    assert call_kwargs["bucket"] == "marketpulse"
    point = call_kwargs["record"]
    # Point serialises to line protocol; check it contains expected tags
    line = point.to_line_protocol()
    assert "symbol=AAPL" in line
    assert "subreddit=wallstreetbets" in line


@pytest.mark.asyncio
async def test_write_with_explicit_timestamp(repo, client):
    write_api = client.write_api.return_value
    ts = datetime(2024, 1, 15, 12, 0, 0)
    await repo.write("AAPL", "stocks", count=5, timestamp=ts)
    write_api.write.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_recent_returns_empty_list(repo, client):
    client.query_api.return_value.query = AsyncMock(return_value=[])
    result = await repo.get_recent("AAPL", hours=24)
    assert result == []


@pytest.mark.asyncio
async def test_get_recent_parses_records(repo, client):
    ts = datetime(2024, 1, 15)
    record = MockRecord(ts, {"symbol": "AAPL", "subreddit": "wsb", "count": 5, "avg_score": 0.3})
    table = MockTable([record])
    client.query_api.return_value.query = AsyncMock(return_value=[table])

    results = await repo.get_recent("AAPL")
    assert len(results) == 1
    assert results[0]["symbol"] == "AAPL"
    assert results[0]["count"] == 5


@pytest.mark.asyncio
async def test_get_rolling_total_empty(repo, client):
    client.query_api.return_value.query = AsyncMock(return_value=[])
    total = await repo.get_rolling_total("AAPL")
    assert total == 0


@pytest.mark.asyncio
async def test_get_rolling_total_sums_count(repo, client):
    record = MockRecord(datetime.now(), {"count": 42})
    table = MockTable([record])
    client.query_api.return_value.query = AsyncMock(return_value=[table])
    total = await repo.get_rolling_total("AAPL")
    assert total == 42


@pytest.mark.asyncio
async def test_get_recent_with_subreddit_filter_adds_flux(repo, client):
    client.query_api.return_value.query = AsyncMock(return_value=[])
    await repo.get_recent("AAPL", subreddit="investing")
    flux = client.query_api.return_value.query.call_args[0][0]
    assert 'r.subreddit == "investing"' in flux
