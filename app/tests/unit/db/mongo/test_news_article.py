from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from db.mongo.news_article import NewsArticleRepository
from domain.news import NewsArticle
from pymongo.errors import DuplicateKeyError


def make_article(**kwargs):
    defaults = dict(
        url="https://example.com/1",
        headline="Apple earnings",
        symbol="AAPL",
        source="reuters",
        published_at=datetime(2024, 1, 15),
    )
    defaults.update(kwargs)
    return NewsArticle(**defaults)


def make_mongo_doc(**kwargs):
    a = make_article(**kwargs)
    doc = a.to_mongo_doc()
    doc["_id"] = "mongo-id"
    return doc


def make_cursor(docs: list[dict]):
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
    col.find_one = AsyncMock(return_value=None)
    col.find = MagicMock(return_value=make_cursor([]))
    col.update_one = AsyncMock()
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=col)
    r = NewsArticleRepository(db)
    r.col = col
    return r, col


@pytest.mark.asyncio
async def test_initialize_creates_indexes(repo):
    r, col = repo
    await r.initialize()
    assert col.create_index.await_count == 3


@pytest.mark.asyncio
async def test_insert_returns_true_on_success(repo):
    r, col = repo
    col.insert_one = AsyncMock()
    result = await r.insert(make_article())
    assert result is True
    col.insert_one.assert_awaited_once()


@pytest.mark.asyncio
async def test_insert_returns_false_on_duplicate(repo):
    r, col = repo
    col.insert_one = AsyncMock(side_effect=DuplicateKeyError("dup"))
    result = await r.insert(make_article())
    assert result is False


@pytest.mark.asyncio
async def test_get_recent_returns_domain_objects(repo):
    r, col = repo
    doc = make_mongo_doc()
    col.find = MagicMock(return_value=make_cursor([doc]))
    results = await r.get_recent("AAPL", hours=24)
    assert len(results) == 1
    assert isinstance(results[0], NewsArticle)
    assert results[0].symbol == "AAPL"


@pytest.mark.asyncio
async def test_get_recent_filters_by_symbol(repo):
    r, col = repo
    col.find = MagicMock(return_value=make_cursor([]))
    await r.get_recent("MSFT", hours=12)
    call_filter = col.find.call_args[0][0]
    assert call_filter["symbol"] == "MSFT"


@pytest.mark.asyncio
async def test_get_unscored_filters_finbert_none(repo):
    r, col = repo
    col.find = MagicMock(return_value=make_cursor([]))
    await r.get_unscored(limit=10)
    call_filter = col.find.call_args[0][0]
    assert call_filter["finbert_score"] is None


@pytest.mark.asyncio
async def test_update_score_calls_update_one(repo):
    r, col = repo
    await r.update_score("https://example.com/1", vader_score=0.5, finbert_score=0.3)
    col.update_one.assert_awaited_once()
    filter_arg = col.update_one.call_args[0][0]
    assert filter_arg["url"] == "https://example.com/1"
    update_arg = col.update_one.call_args[0][1]
    assert update_arg["$set"]["vader_score"] == 0.5
    assert update_arg["$set"]["finbert_score"] == 0.3
