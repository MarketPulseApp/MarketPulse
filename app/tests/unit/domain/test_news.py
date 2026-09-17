from __future__ import annotations

from datetime import datetime

import pytest
from domain.news import NewsArticle


def make_article(**kwargs) -> NewsArticle:
    defaults = dict(
        url="https://example.com/article",
        headline="Apple beats earnings",
        symbol="AAPL",
        source="reuters",
        published_at=datetime(2024, 1, 15, 12, 0, 0),
    )
    defaults.update(kwargs)
    return NewsArticle(**defaults)


# ── construction ─────────────────────────────────────────────────────────────


def test_minimal_construction():
    a = make_article()
    assert a.url == "https://example.com/article"
    assert a.summary == ""
    assert a.vader_score is None
    assert a.finbert_score is None
    assert a.embedding is None


def test_full_construction():
    a = make_article(
        summary="Strong quarter",
        vader_score=0.8,
        finbert_score=0.7,
        embedding=[0.1, 0.2, 0.3],
    )
    assert a.vader_score == 0.8
    assert a.finbert_score == 0.7
    assert a.embedding == [0.1, 0.2, 0.3]


# ── properties ───────────────────────────────────────────────────────────────


def test_is_scored_false_when_missing_both():
    assert make_article().is_scored is False


def test_is_scored_false_when_missing_one():
    assert make_article(vader_score=0.5).is_scored is False
    assert make_article(finbert_score=0.5).is_scored is False


def test_is_scored_true_when_both_present():
    assert make_article(vader_score=0.5, finbert_score=0.3).is_scored is True


def test_composite_sentiment_none_when_missing():
    assert make_article().composite_sentiment is None
    assert make_article(vader_score=0.5).composite_sentiment is None


def test_composite_sentiment_averages():
    a = make_article(vader_score=0.8, finbert_score=0.6)
    assert a.composite_sentiment == pytest.approx(0.7)


def test_composite_sentiment_negative():
    a = make_article(vader_score=-0.4, finbert_score=-0.6)
    assert a.composite_sentiment == pytest.approx(-0.5)


# ── to_mongo_doc ─────────────────────────────────────────────────────────────


def test_to_mongo_doc_excludes_embedding():
    a = make_article(embedding=[0.1, 0.2])
    doc = a.to_mongo_doc()
    assert "embedding" not in doc


def test_to_mongo_doc_contains_expected_keys():
    doc = make_article().to_mongo_doc()
    for key in ("url", "headline", "symbol", "source", "published_at", "summary"):
        assert key in doc


def test_to_mongo_doc_values():
    a = make_article(vader_score=0.5, finbert_score=0.3)
    doc = a.to_mongo_doc()
    assert doc["symbol"] == "AAPL"
    assert doc["vader_score"] == 0.5


# ── from_mongo_doc ───────────────────────────────────────────────────────────


def test_from_mongo_doc_drops_id():
    doc = make_article().to_mongo_doc()
    doc["_id"] = "some-mongo-id"
    a = NewsArticle.from_mongo_doc(doc)
    assert a.url == "https://example.com/article"


def test_from_mongo_doc_roundtrip():
    original = make_article(vader_score=0.5, summary="test")
    doc = original.to_mongo_doc()
    restored = NewsArticle.from_mongo_doc(doc)
    assert restored.url == original.url
    assert restored.vader_score == original.vader_score
    assert restored.summary == original.summary


# ── to_elastic_doc ───────────────────────────────────────────────────────────


def test_to_elastic_doc_excludes_embedding():
    a = make_article(embedding=[0.1])
    doc = a.to_elastic_doc()
    assert "embedding" not in doc


def test_to_elastic_doc_excludes_url():
    doc = make_article().to_elastic_doc()
    assert "url" not in doc


def test_to_elastic_doc_isoformat_date():
    a = make_article()
    doc = a.to_elastic_doc()
    assert isinstance(doc["published_at"], str)
    assert "2024-01-15" in doc["published_at"]
