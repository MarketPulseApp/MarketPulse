from __future__ import annotations

import pytest
from db.embedded.live_aggregation import LiveAggregationRepository


@pytest.fixture
def repo():
    return LiveAggregationRepository()


@pytest.mark.asyncio
async def test_get_daily_summary_empty(repo):
    results = await repo.get_daily_summary()
    assert results == []


@pytest.mark.asyncio
async def test_get_top_movers_empty(repo):
    results = await repo.get_top_movers()
    assert results == []


@pytest.mark.asyncio
async def test_query_runs_sql(repo):
    results = await repo.query("SELECT 1 AS val")
    assert results[0]["val"] == 1


@pytest.mark.asyncio
async def test_query_with_params(repo):
    results = await repo.query("SELECT ? AS val", [42])
    assert results[0]["val"] == 42


@pytest.mark.asyncio
async def test_get_top_movers_after_insert(repo):
    repo._conn.execute(
        """
        INSERT INTO ohlcv_today VALUES
            ('AAPL', 150.0, 160.0, 148.0, 158.0, 1000000, '2024-01-15 09:30:00'),
            ('MSFT', 300.0, 310.0, 298.0, 305.0, 500000,  '2024-01-15 09:30:00'),
            ('GME',  10.0,  50.0,  9.0,   45.0,  9000000, '2024-01-15 09:30:00')
    """
    )
    movers = await repo.get_top_movers(n=3)
    assert len(movers) == 3
    # GME had the biggest move (350%)
    assert movers[0]["symbol"] == "GME"


@pytest.mark.asyncio
async def test_get_daily_summary_after_insert(repo):
    repo._conn.execute(
        """
        INSERT INTO ohlcv_today VALUES
            ('AAPL', 150.0, 160.0, 148.0, 158.0, 1000000, '2024-01-15 09:30:00'),
            ('AAPL', 158.0, 162.0, 156.0, 160.0, 800000,  '2024-01-15 10:00:00')
    """
    )
    summary = await repo.get_daily_summary()
    assert len(summary) == 1
    row = summary[0]
    assert row["symbol"] == "AAPL"
    assert row["total_volume"] == 1800000
    assert row["bar_count"] == 2


@pytest.mark.asyncio
async def test_refresh_replaces_data(repo):
    # patch the sync _load_from_parquet to simulate reload
    original_load = repo._load_from_parquet
    loaded = []

    def mock_load(glob):
        loaded.append(glob)
        repo._conn.execute("DELETE FROM ohlcv_today")

    repo._load_from_parquet = mock_load
    await repo.refresh("/data/*.parquet")
    assert loaded == ["/data/*.parquet"]
    repo._load_from_parquet = original_load
