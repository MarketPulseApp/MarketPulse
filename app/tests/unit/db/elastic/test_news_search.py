from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from db.elastic.news_search import NewsSearchRepository


def make_hit(source: dict) -> dict:
    return {"_source": source}


def make_search_response(hits: list[dict]) -> dict:
    return {"hits": {"hits": [make_hit(h) for h in hits]}}


@pytest.fixture
def client():
    es = AsyncMock()
    es.indices = AsyncMock()
    es.indices.exists = AsyncMock(return_value=False)
    es.indices.create = AsyncMock()
    es.index = AsyncMock()
    es.delete = AsyncMock()
    es.search = AsyncMock(return_value=make_search_response([]))
    return es


@pytest.fixture
def repo(client):
    return NewsSearchRepository(client)


@pytest.mark.asyncio
async def test_initialize_creates_index_when_not_exists(repo, client):
    client.indices.exists = AsyncMock(return_value=False)
    await repo.initialize()
    client.indices.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_initialize_skips_when_index_exists(repo, client):
    client.indices.exists = AsyncMock(return_value=True)
    await repo.initialize()
    client.indices.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_index_uses_url_as_doc_id(repo, client):
    article = {
        "url": "https://example.com/1",
        "headline": "Test",
        "symbol": "AAPL",
    }
    await repo.index(article)
    client.index.assert_awaited_once()
    call_kwargs = client.index.call_args.kwargs
    assert call_kwargs["id"] == "https://example.com/1"
    assert "url" not in call_kwargs["document"]


@pytest.mark.asyncio
async def test_search_returns_sources(repo, client):
    client.search = AsyncMock(
        return_value=make_search_response(
            [
                {"headline": "Apple up", "symbol": "AAPL"},
                {"headline": "Apple Q4", "symbol": "AAPL"},
            ]
        )
    )
    results = await repo.search("Apple earnings", symbol="AAPL")
    assert len(results) == 2
    assert results[0]["headline"] == "Apple up"


@pytest.mark.asyncio
async def test_search_with_symbol_adds_term_filter(repo, client):
    await repo.search("earnings", symbol="MSFT")
    body = client.search.call_args.kwargs["body"]
    filters = body["query"]["bool"]["filter"]
    term_filters = [f for f in filters if "term" in f]
    assert any(f["term"]["symbol"] == "MSFT" for f in term_filters)


@pytest.mark.asyncio
async def test_search_without_symbol_no_term_filter(repo, client):
    await repo.search("earnings")
    body = client.search.call_args.kwargs["body"]
    filters = body["query"]["bool"]["filter"]
    term_filters = [f for f in filters if "term" in f]
    assert len(term_filters) == 0


@pytest.mark.asyncio
async def test_search_has_multi_match_on_headline_and_summary(repo, client):
    await repo.search("strong quarter")
    body = client.search.call_args.kwargs["body"]
    must = body["query"]["bool"]["must"]
    assert any("multi_match" in clause for clause in must)
    mm = next(c["multi_match"] for c in must if "multi_match" in c)
    assert "headline^2" in mm["fields"]
    assert "summary" in mm["fields"]


@pytest.mark.asyncio
async def test_delete_calls_es_delete(repo, client):
    await repo.delete("https://example.com/1")
    client.delete.assert_awaited_once()
    call_kwargs = client.delete.call_args.kwargs
    assert call_kwargs["index"] == "news_index"
    assert call_kwargs["id"] == "https://example.com/1"
