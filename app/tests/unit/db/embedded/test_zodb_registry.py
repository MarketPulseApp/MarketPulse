from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from db.embedded.zodb_registry import TickerRegistryRepository


@pytest.fixture
def repo(tmp_path):
    # Patch _open_db to avoid needing ZODB installed
    mock_root = {"tickers": {}}

    class FakeOOBTree(dict):
        pass

    mock_root["tickers"] = FakeOOBTree()

    mock_db = MagicMock()
    mock_conn = MagicMock()

    with patch("db.embedded.zodb_registry._open_db", return_value=(mock_db, mock_conn, mock_root)):
        with patch("db.embedded.zodb_registry.transaction") as mock_tx:
            mock_tx.commit = MagicMock()
            mock_tx.abort = MagicMock()
            r = TickerRegistryRepository(str(tmp_path / "data.fs"))
            r._root = mock_root
            r._db = mock_db
            r._connection = mock_conn
            return r, mock_root


@pytest.mark.asyncio
async def test_add_stores_ticker(repo):
    r, root = repo
    with patch("db.embedded.zodb_registry.transaction"):
        await r.add("AAPL", {"name": "Apple Inc.", "sector": "Technology", "is_active": True})
    assert "AAPL" in root["tickers"]


@pytest.mark.asyncio
async def test_get_returns_none_when_missing(repo):
    r, root = repo
    result = await r.get("NONEXISTENT")
    assert result is None


@pytest.mark.asyncio
async def test_get_returns_dict_when_present(repo):
    r, root = repo
    from persistent.mapping import PersistentMapping

    root["tickers"]["MSFT"] = PersistentMapping({"name": "Microsoft", "is_active": True})
    result = await r.get("MSFT")
    assert result is not None
    assert result["name"] == "Microsoft"


@pytest.mark.asyncio
async def test_get_all_returns_all_tickers(repo):
    r, root = repo
    from persistent.mapping import PersistentMapping

    root["tickers"]["AAPL"] = PersistentMapping({"name": "Apple", "is_active": True})
    root["tickers"]["TSLA"] = PersistentMapping({"name": "Tesla", "is_active": True})
    results = await r.get_all()
    assert len(results) == 2


@pytest.mark.asyncio
async def test_get_active_filters_inactive(repo):
    r, root = repo
    from persistent.mapping import PersistentMapping

    root["tickers"]["AAPL"] = PersistentMapping({"name": "Apple", "is_active": True})
    root["tickers"]["GME"] = PersistentMapping({"name": "GameStop", "is_active": False})
    results = await r.get_active()
    symbols = [t["name"] for t in results]
    assert "Apple" in symbols
    assert "GameStop" not in symbols


@pytest.mark.asyncio
async def test_deactivate_sets_is_active_false(repo):
    r, root = repo
    from persistent.mapping import PersistentMapping

    root["tickers"]["BB"] = PersistentMapping({"name": "BlackBerry", "is_active": True})
    with patch("db.embedded.zodb_registry.transaction"):
        await r.deactivate("BB")
    assert root["tickers"]["BB"]["is_active"] is False


@pytest.mark.asyncio
async def test_delete_removes_ticker(repo):
    r, root = repo
    from persistent.mapping import PersistentMapping

    root["tickers"]["DEL"] = PersistentMapping({"name": "DeleteMe", "is_active": True})
    with patch("db.embedded.zodb_registry.transaction"):
        await r.delete("DEL")
    assert "DEL" not in root["tickers"]
