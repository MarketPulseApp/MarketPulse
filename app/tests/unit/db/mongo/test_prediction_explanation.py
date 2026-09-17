from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from db.mongo.prediction_explanation import PredictionExplanationRepository
from domain.explanation import PredictionExplanation


def make_explanation(**kwargs):
    defaults = dict(
        prediction_id="pred-001",
        symbol="AAPL",
        horizon="1d",
        direction="up",
        confidence=0.75,
        features=[{"name": "rsi", "value": 60.0, "shap_value": 0.04, "rank": 1}],
        explanation="Bullish signal from RSI.",
    )
    defaults.update(kwargs)
    return PredictionExplanation(**defaults)


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
    col.find_one = AsyncMock(return_value=None)
    col.find = MagicMock(return_value=make_cursor([]))
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=col)
    r = PredictionExplanationRepository(db)
    r.col = col
    return r, col


@pytest.mark.asyncio
async def test_initialize_creates_indexes(repo):
    r, col = repo
    await r.initialize()
    assert col.create_index.await_count == 2


@pytest.mark.asyncio
async def test_insert_calls_insert_one(repo):
    r, col = repo
    await r.insert(make_explanation())
    col.insert_one.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_for_prediction_not_found(repo):
    r, col = repo
    col.find_one = AsyncMock(return_value=None)
    result = await r.get_for_prediction("missing-id")
    assert result is None


@pytest.mark.asyncio
async def test_get_for_prediction_found(repo):
    r, col = repo
    doc = make_explanation().to_mongo_doc()
    doc["_id"] = "mid"
    col.find_one = AsyncMock(return_value=doc)
    result = await r.get_for_prediction("pred-001")
    assert isinstance(result, PredictionExplanation)
    assert result.prediction_id == "pred-001"


@pytest.mark.asyncio
async def test_get_recent_returns_list(repo):
    r, col = repo
    doc = make_explanation().to_mongo_doc()
    doc["_id"] = "mid"
    col.find = MagicMock(return_value=make_cursor([doc]))
    results = await r.get_recent("AAPL", limit=5)
    assert len(results) == 1
    assert isinstance(results[0], PredictionExplanation)
