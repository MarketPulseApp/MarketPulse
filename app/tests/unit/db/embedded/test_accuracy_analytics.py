from __future__ import annotations

from datetime import datetime

import pytest
from db.embedded.accuracy_analytics import AccuracyAnalyticsRepository


def make_row(**kwargs):
    defaults = dict(
        id="pred-001",
        symbol="AAPL",
        horizon="1d",
        direction="up",
        confidence=0.75,
        was_correct=True,
        resolved_at=datetime(2024, 1, 16),
        predicted_at=datetime(2024, 1, 15),
    )
    defaults.update(kwargs)
    return defaults


@pytest.fixture
def repo(tmp_path):
    return AccuracyAnalyticsRepository(str(tmp_path / "accuracy.db"))


@pytest.mark.asyncio
async def test_insert_and_get_overall_accuracy(repo):
    await repo.insert_resolved(make_row(id="p1", was_correct=True))
    await repo.insert_resolved(make_row(id="p2", was_correct=False))
    result = await repo.get_overall_accuracy("AAPL", "1d")
    assert result["total"] == 2
    assert result["correct"] == 1
    assert result["accuracy"] == pytest.approx(0.5)


@pytest.mark.asyncio
async def test_insert_ignores_duplicate_id(repo):
    await repo.insert_resolved(make_row(id="dup"))
    await repo.insert_resolved(make_row(id="dup"))  # should be ignored
    result = await repo.get_overall_accuracy("AAPL", "1d")
    assert result["total"] == 1


@pytest.mark.asyncio
async def test_overall_accuracy_empty(repo):
    result = await repo.get_overall_accuracy("AAPL", "1d")
    assert result["total"] == 0
    assert result["accuracy"] == 0.0


@pytest.mark.asyncio
async def test_rolling_accuracy_all_correct(repo):
    for i in range(5):
        await repo.insert_resolved(make_row(id=f"p{i}", was_correct=True))
    acc = await repo.get_rolling_accuracy("AAPL", "1d", window=5)
    assert acc == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_rolling_accuracy_all_wrong(repo):
    for i in range(5):
        await repo.insert_resolved(make_row(id=f"p{i}", was_correct=False))
    acc = await repo.get_rolling_accuracy("AAPL", "1d", window=5)
    assert acc == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_rolling_accuracy_window_limits_rows(repo):
    # Insert 10, window=3 → only last 3 considered
    for i in range(10):
        correct = i >= 7  # last 3 are correct
        await repo.insert_resolved(
            make_row(
                id=f"p{i}",
                was_correct=correct,
                resolved_at=datetime(2024, 1, i + 1),
            )
        )
    acc = await repo.get_rolling_accuracy("AAPL", "1d", window=3)
    assert acc == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_calibration_returns_buckets(repo):
    for i in range(10):
        await repo.insert_resolved(make_row(id=f"p{i}", confidence=0.8, was_correct=(i % 2 == 0)))
    cal = await repo.get_calibration("AAPL", "1d", buckets=10)
    assert len(cal) >= 1
    assert "conf_bin" in cal[0]
    assert "accuracy" in cal[0]
    assert "n" in cal[0]


@pytest.mark.asyncio
async def test_rolling_accuracy_empty(repo):
    acc = await repo.get_rolling_accuracy("AAPL", "1d")
    assert acc == 0.0
