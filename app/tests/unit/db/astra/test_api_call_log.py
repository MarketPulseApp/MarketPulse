from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from db.astra.api_call_log import APICallLogRepository


def make_session(rows=None):
    stmt = MagicMock()
    session = MagicMock()
    session.prepare.return_value = stmt

    if rows is None:
        rows = []
    fake_rows = []
    for r in rows:
        mock_row = MagicMock()
        mock_row.source = r["source"]
        mock_row.logged_at = r.get("logged_at", datetime.utcnow())
        mock_row.endpoint = r["endpoint"]
        mock_row.status_code = r["status_code"]
        mock_row.latency_ms = r["latency_ms"]
        mock_row.error_msg = r.get("error_msg")
        fake_rows.append(mock_row)

    session.execute.return_value = iter(fake_rows)
    return session


@pytest.fixture
def repo():
    session = make_session()
    return APICallLogRepository(session, keyspace="marketpulse"), session


@pytest.mark.asyncio
async def test_log_calls_session_execute(repo):
    r, session = repo
    await r.log("alphavantage", "/query", 200, 142)
    session.execute.assert_called()


@pytest.mark.asyncio
async def test_log_passes_correct_args(repo):
    r, session = repo
    await r.log("polygon", "/v2/aggs", 429, 50, error_msg="rate limited")
    call_args = session.execute.call_args[0]
    # Second arg is the bound values tuple
    values = call_args[1]
    assert values[0] == "polygon"
    assert values[2] == "/v2/aggs"
    assert values[3] == 429
    assert values[4] == 50
    assert values[5] == "rate limited"


@pytest.mark.asyncio
async def test_log_none_error_msg(repo):
    r, session = repo
    await r.log("sec", "/submissions", 200, 300)
    call_args = session.execute.call_args[0]
    values = call_args[1]
    assert values[5] is None


@pytest.mark.asyncio
async def test_get_recent_returns_mapped_dicts(repo):
    r, session = repo
    session.execute.return_value = iter([])
    session_with_rows = make_session(
        [
            {"source": "polygon", "endpoint": "/v2", "status_code": 200, "latency_ms": 100},
        ]
    )
    session_with_rows.prepare.return_value = session.prepare.return_value
    r2 = APICallLogRepository(session_with_rows, keyspace="marketpulse")

    results = await r2.get_recent("polygon", limit=10)
    assert len(results) == 1
    assert results[0]["source"] == "polygon"
    assert results[0]["status_code"] == 200


@pytest.mark.asyncio
async def test_get_recent_empty(repo):
    r, session = repo
    session.execute.return_value = iter([])
    results = await r.get_recent("missing_source")
    assert results == []


def test_prepares_statements_on_init():
    session = MagicMock()
    session.prepare.return_value = MagicMock()
    APICallLogRepository(session, keyspace="test")
    assert session.prepare.call_count == 2
