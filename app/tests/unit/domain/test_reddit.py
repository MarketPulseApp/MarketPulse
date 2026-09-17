from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from domain.reddit import RedditPost


def make_post(**kwargs) -> RedditPost:
    defaults = dict(
        post_id="abc123",
        subreddit="wallstreetbets",
        title="AAPL to the moon",
        body="Strong fundamentals",
        symbol="AAPL",
        score=500,
        created_at=datetime(2024, 1, 15, 9, 30, 0),
    )
    defaults.update(kwargs)
    return RedditPost(**defaults)


def test_minimal_construction():
    p = make_post()
    assert p.post_id == "abc123"
    assert p.url == ""
    assert p.author == ""
    assert p.flair is None
    assert p.num_comments == 0
    assert p.sentiment_score is None
    assert p.embedding is None


def test_full_text_title_only():
    p = make_post(body="")
    assert p.full_text == "AAPL to the moon"


def test_full_text_title_and_body():
    p = make_post(title="Hello", body="World")
    assert p.full_text == "Hello World"


def test_is_scored_false_when_none():
    assert make_post().is_scored is False


def test_is_scored_true_when_set():
    assert make_post(sentiment_score=0.5).is_scored is True


def test_is_bullish_none_when_unscored():
    assert make_post().is_bullish is None


def test_is_bullish_true_above_threshold():
    assert make_post(sentiment_score=0.1).is_bullish is True


def test_is_bullish_false_below_threshold():
    assert make_post(sentiment_score=-0.1).is_bullish is False


def test_is_bullish_none_in_neutral_band():
    assert make_post(sentiment_score=0.03).is_bullish is None
    assert make_post(sentiment_score=-0.03).is_bullish is None


def test_to_mongo_doc_excludes_embedding():
    p = make_post(embedding=[0.1, 0.2])
    doc = p.to_mongo_doc()
    assert "embedding" not in doc


def test_to_mongo_doc_contains_expected_keys():
    doc = make_post().to_mongo_doc()
    for key in ("post_id", "subreddit", "title", "body", "symbol", "score", "created_at"):
        assert key in doc


def test_from_mongo_doc_drops_id():
    doc = make_post().to_mongo_doc()
    doc["_id"] = "mongo-id"
    p = RedditPost.from_mongo_doc(doc)
    assert p.post_id == "abc123"


def test_from_mongo_doc_roundtrip():
    original = make_post(sentiment_score=0.7, flair="DD")
    doc = original.to_mongo_doc()
    restored = RedditPost.from_mongo_doc(doc)
    assert restored.post_id == original.post_id
    assert restored.sentiment_score == original.sentiment_score
    assert restored.flair == original.flair


def test_from_praw():
    submission = MagicMock()
    submission.id = "xyz789"
    submission.subreddit.__str__ = lambda _: "stocks"
    submission.title = "MSFT earnings"
    submission.selftext = "Great quarter"
    submission.score = 100
    submission.created_utc = 1705312200.0  # 2024-01-15 09:30:00 UTC
    submission.permalink = "/r/stocks/comments/xyz789/"
    submission.author.__str__ = lambda _: "trader_joe"
    submission.link_flair_text = "DD"
    submission.num_comments = 42

    p = RedditPost.from_praw(submission, symbol="MSFT")
    assert p.post_id == "xyz789"
    assert p.symbol == "MSFT"
    assert p.subreddit == "stocks"
    assert p.flair == "DD"
    assert p.num_comments == 42
    assert "reddit.com" in p.url


def test_from_praw_deleted_author():
    submission = MagicMock()
    submission.id = "del1"
    submission.subreddit.__str__ = lambda _: "investing"
    submission.title = "Test"
    submission.selftext = ""
    submission.score = 0
    submission.created_utc = 1705312200.0
    submission.permalink = "/r/investing/comments/del1/"
    submission.author = None
    submission.link_flair_text = None
    submission.num_comments = 0

    p = RedditPost.from_praw(submission, symbol="TSLA")
    assert p.author == "[deleted]"
