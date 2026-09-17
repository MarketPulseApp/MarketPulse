from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from db.mongo.sec_filing import SECFilingRepository
from domain.sec import SECFiling
from pymongo.errors import DuplicateKeyError


def make_filing(**kwargs):
    defaults = dict(
        filing_id="0000320193-24-000123",
        ticker="AAPL",
        cik="0000320193",
        form_type="10-K",
        filed_at=datetime(2024, 11, 1),
        content="Annual report content",
    )
    defaults.update(kwargs)
    return SECFiling(**defaults)


def make_cursor(docs):
    cursor = MagicMock()
    cursor.sort.return_value = cursor
    cursor.limit.return_value = cursor
    cursor.to_list = AsyncMock(return_value=docs)
    return cursor


@pytest.fixture
def repo():
    col = MagicMock()
    col.create_index = AsyncMock()
    col.insert_one = AsyncMock()
    col.find = MagicMock(return_value=make_cursor([]))
    col.update_one = AsyncMock()
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=col)
    r = SECFilingRepository(db)
    r.col = col
    return r, col


@pytest.mark.asyncio
async def test_initialize_creates_indexes(repo):
    r, col = repo
    await r.initialize()
    assert col.create_index.await_count == 3


@pytest.mark.asyncio
async def test_insert_returns_true(repo):
    r, col = repo
    assert await r.insert(make_filing()) is True


@pytest.mark.asyncio
async def test_insert_returns_false_on_duplicate(repo):
    r, col = repo
    col.insert_one = AsyncMock(side_effect=DuplicateKeyError("dup"))
    assert await r.insert(make_filing()) is False


@pytest.mark.asyncio
async def test_get_recent_returns_filings(repo):
    r, col = repo
    doc = make_filing().to_mongo_doc()
    doc["_id"] = "id"
    col.find = MagicMock(return_value=make_cursor([doc]))
    results = await r.get_recent("AAPL")
    assert len(results) == 1
    assert isinstance(results[0], SECFiling)


@pytest.mark.asyncio
async def test_get_recent_with_form_type_filter(repo):
    r, col = repo
    await r.get_recent("AAPL", form_type="10-Q")
    filt = col.find.call_args[0][0]
    assert filt["form_type"] == "10-Q"


@pytest.mark.asyncio
async def test_get_recent_no_form_type_filter(repo):
    r, col = repo
    await r.get_recent("AAPL")
    filt = col.find.call_args[0][0]
    assert "form_type" not in filt


@pytest.mark.asyncio
async def test_get_unsummarised_filters_none_summary(repo):
    r, col = repo
    await r.get_unsummarised()
    filt = col.find.call_args[0][0]
    assert filt["summary"] == {"$in": [None, ""]}


@pytest.mark.asyncio
async def test_update_summary(repo):
    r, col = repo
    await r.update_summary("0000320193-24-000123", "This is a summary")
    col.update_one.assert_awaited_once()
    filt = col.update_one.call_args[0][0]
    assert filt["filing_id"] == "0000320193-24-000123"
    update = col.update_one.call_args[0][1]
    assert update["$set"]["summary"] == "This is a summary"
