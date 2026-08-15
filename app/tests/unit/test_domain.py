"""
app/tests/unit/test_domain.py

Unit tests for all Phase 3 domain model classes.
Run with: pytest app/tests/unit/test_domain.py -v
"""

import math
from datetime import UTC, datetime

import pytest

from app.domain.alert import Alert, AlertConfig
from app.domain.feature_vector import CURRENT_SCHEMA_VERSION, FeatureVector
from app.domain.prediction import HorizonPrediction, Prediction, PredictionOutcome
from app.domain.quota import APIQuota, QuotaStatus
from app.domain.sentiment import NewsArticle, RedditPost, SentimentScore
from app.domain.ticker import CryptoTicker, IndexTicker, StockTicker, Ticker
from app.domain.watchlist import WatchList
from app.events.types import PredictionChangedEvent

# ── Ticker ────────────────────────────────────────────────────────────────────


class TestTicker:
    def test_is_stock_returns_true_for_stock(self):
        ticker = Ticker(symbol="AAPL", name="Apple Inc.", asset_type="stock")
        assert ticker.is_stock() is True

    def test_is_stock_returns_false_for_crypto(self):
        ticker = Ticker(symbol="BTC-USD", name="Bitcoin", asset_type="crypto")
        assert ticker.is_stock() is False

    def test_is_crypto_returns_true_for_crypto(self):
        ticker = Ticker(symbol="ETH-USD", name="Ethereum", asset_type="crypto")
        assert ticker.is_crypto() is True

    def test_is_crypto_returns_false_for_stock(self):
        ticker = Ticker(symbol="TSLA", name="Tesla", asset_type="stock")
        assert ticker.is_crypto() is False

    def test_get_display_name_returns_name(self):
        ticker = Ticker(symbol="AAPL", name="Apple Inc.", asset_type="stock")
        assert ticker.get_display_name() == "Apple Inc."

    def test_subreddits_defaults_to_empty_list(self):
        ticker = Ticker(symbol="AAPL", name="Apple Inc.", asset_type="stock")
        assert ticker.subreddits == []

    def test_is_active_defaults_to_true(self):
        ticker = Ticker(symbol="AAPL", name="Apple Inc.", asset_type="stock")
        assert ticker.is_active is True


class TestStockTicker:
    def test_stock_ticker_has_exchange_field(self):
        ticker = StockTicker(
            symbol="AAPL", name="Apple Inc.", asset_type="stock", exchange="NASDAQ"
        )
        assert ticker.exchange == "NASDAQ"

    def test_stock_ticker_exchange_defaults_to_none(self):
        ticker = StockTicker(symbol="AAPL", name="Apple Inc.", asset_type="stock")
        assert ticker.exchange is None

    def test_stock_ticker_inherits_is_stock(self):
        ticker = StockTicker(symbol="AAPL", name="Apple Inc.", asset_type="stock")
        assert ticker.is_stock() is True


class TestCryptoTicker:
    def test_crypto_ticker_has_chain_and_coingecko_id(self):
        ticker = CryptoTicker(
            symbol="ETH-USD",
            name="Ethereum",
            asset_type="crypto",
            chain="ethereum",
            coingecko_id="ethereum",
        )
        assert ticker.chain == "ethereum"
        assert ticker.coingecko_id == "ethereum"

    def test_crypto_ticker_fields_default_to_none(self):
        ticker = CryptoTicker(symbol="ETH-USD", name="Ethereum", asset_type="crypto")
        assert ticker.chain is None
        assert ticker.coingecko_id is None

    def test_crypto_ticker_inherits_is_crypto(self):
        ticker = CryptoTicker(symbol="BTC-USD", name="Bitcoin", asset_type="crypto")
        assert ticker.is_crypto() is True


class TestIndexTicker:
    def test_index_ticker_can_be_instantiated(self):
        ticker = IndexTicker(symbol="SPY", name="S&P 500 ETF", asset_type="etf")
        assert ticker.symbol == "SPY"


# ── Prediction ────────────────────────────────────────────────────────────────


class TestPrediction:
    def _make_prediction(self, confidence: float) -> Prediction:
        return Prediction(
            symbol="AAPL",
            horizon="1d",
            direction="UP",
            confidence=confidence,
            prediction_time=datetime.now(UTC),
        )

    def test_is_actionable_returns_false_at_74_9(self):
        assert self._make_prediction(74.9).is_actionable() is False

    def test_is_actionable_returns_true_at_75_0(self):
        assert self._make_prediction(75.0).is_actionable() is True

    def test_is_actionable_returns_true_above_75(self):
        assert self._make_prediction(99.9).is_actionable() is True

    def test_is_actionable_returns_false_at_zero(self):
        assert self._make_prediction(0.0).is_actionable() is False

    def test_is_actionable_returns_false_below_threshold(self):
        assert self._make_prediction(50.0).is_actionable() is False


class TestHorizonPrediction:
    def test_horizon_prediction_stores_fields(self):
        hp = HorizonPrediction(
            horizon="7d",
            direction="DOWN",
            confidence=82.5,
            lstm_confidence=80.0,
            xgb_confidence=85.0,
            lgbm_confidence=82.0,
        )
        assert hp.horizon == "7d"
        assert hp.direction == "DOWN"
        assert hp.confidence == 82.5

    def test_component_scores_default_to_none(self):
        hp = HorizonPrediction(horizon="1d", direction="FLAT", confidence=60.0)
        assert hp.lstm_confidence is None
        assert hp.xgb_confidence is None
        assert hp.lgbm_confidence is None


class TestPredictionOutcome:
    def test_prediction_outcome_stores_fields(self):
        outcome = PredictionOutcome(
            symbol="AAPL",
            horizon="1d",
            prediction_time=datetime(2026, 1, 1, tzinfo=UTC),
            outcome_time=datetime(2026, 1, 2, tzinfo=UTC),
            actual_direction="UP",
            was_correct=True,
        )
        assert outcome.was_correct is True
        assert outcome.actual_direction == "UP"


# ── SentimentScore ────────────────────────────────────────────────────────────


class TestSentimentScore:
    def test_score_within_range_is_unchanged(self):
        s = SentimentScore(symbol="AAPL", source_type="news", score=0.5)
        assert s.score == 0.5

    def test_score_at_upper_bound_is_unchanged(self):
        s = SentimentScore(symbol="AAPL", source_type="news", score=1.0)
        assert s.score == 1.0

    def test_score_at_lower_bound_is_unchanged(self):
        s = SentimentScore(symbol="AAPL", source_type="news", score=-1.0)
        assert s.score == -1.0

    def test_score_above_1_is_clamped_to_1(self):
        s = SentimentScore(symbol="AAPL", source_type="news", score=1.5)
        assert s.score == 1.0

    def test_score_below_minus_1_is_clamped_to_minus_1(self):
        s = SentimentScore(symbol="AAPL", source_type="news", score=-2.0)
        assert s.score == -1.0

    def test_zero_score_is_unchanged(self):
        s = SentimentScore(symbol="AAPL", source_type="news", score=0.0)
        assert s.score == 0.0


class TestNewsArticle:
    def test_news_article_stores_fields(self):
        article = NewsArticle(
            symbol="AAPL",
            headline="Apple hits record high",
            url="https://example.com/article",
            source="NewsAPI",
            published_at=datetime.now(UTC),
            finbert_score=0.85,
        )
        assert article.symbol == "AAPL"
        assert article.finbert_score == 0.85

    def test_optional_fields_default_to_none(self):
        article = NewsArticle(
            symbol="AAPL",
            headline="Apple news",
            url="https://example.com",
            source="NewsAPI",
            published_at=datetime.now(UTC),
        )
        assert article.finbert_score is None
        assert article.summary is None


class TestRedditPost:
    def test_reddit_post_stores_fields(self):
        post = RedditPost(
            symbol="GME",
            subreddit="wallstreetbets",
            title="GME to the moon",
            url="https://reddit.com/r/wallstreetbets/post",
            score=5000,
            created_utc=datetime.now(UTC),
        )
        assert post.subreddit == "wallstreetbets"
        assert post.score == 5000

    def test_optional_fields_default_to_none_or_zero(self):
        post = RedditPost(
            symbol="GME",
            subreddit="wallstreetbets",
            title="GME to the moon",
            url="https://reddit.com/r/wallstreetbets/post",
            score=100,
            created_utc=datetime.now(UTC),
        )
        assert post.vader_score is None
        assert post.comment_count == 0


# ── Alert ─────────────────────────────────────────────────────────────────────


class TestAlertConfig:
    def test_raises_value_error_when_channels_empty(self):
        with pytest.raises(ValueError):
            AlertConfig(
                user_id="user-123",
                alert_type="high_confidence",
                channels=[],
            )

    def test_does_not_raise_with_valid_channels(self):
        config = AlertConfig(
            user_id="user-123",
            alert_type="high_confidence",
            channels=["email", "discord"],
        )
        assert config.channels == ["email", "discord"]

    def test_symbol_defaults_to_none(self):
        config = AlertConfig(
            user_id="user-123",
            alert_type="high_confidence",
            channels=["email"],
        )
        assert config.symbol is None

    def test_is_enabled_defaults_to_true(self):
        config = AlertConfig(
            user_id="user-123",
            alert_type="high_confidence",
            channels=["email"],
        )
        assert config.is_enabled is True


class TestAlertShouldFire:
    def _make_alert(self, threshold=None, current=None) -> Alert:
        return Alert(
            alert_type="high_confidence",
            symbol="AAPL",
            message="Test alert",
            channels=["email"],
            threshold_value=threshold,
            current_value=current,
        )

    def test_fires_when_no_threshold(self):
        assert self._make_alert(threshold=None, current=None).should_fire() is True

    def test_fires_when_current_value_equals_threshold(self):
        assert self._make_alert(threshold=80.0, current=80.0).should_fire() is True

    def test_fires_when_current_value_exceeds_threshold(self):
        assert self._make_alert(threshold=80.0, current=95.0).should_fire() is True

    def test_does_not_fire_when_current_below_threshold(self):
        assert self._make_alert(threshold=80.0, current=79.9).should_fire() is False

    def test_fires_when_current_value_is_none(self):
        assert self._make_alert(threshold=80.0, current=None).should_fire() is True


class TestAlertFromEvent:
    def _make_config(self) -> AlertConfig:
        return AlertConfig(
            user_id="user-123",
            alert_type="prediction_changed",
            channels=["email", "discord"],
            symbol="AAPL",
            threshold_value=75.0,
        )

    def test_from_event_creates_alert(self):
        event = PredictionChangedEvent(
            symbol="AAPL",
            old_direction="FLAT",
            new_direction="UP",
            confidence=87.5,
            horizon="1d",
        )
        alert = Alert.from_event(event, self._make_config())
        assert isinstance(alert, Alert)

    def test_from_event_copies_symbol(self):
        event = PredictionChangedEvent(
            symbol="AAPL",
            old_direction="FLAT",
            new_direction="UP",
            confidence=87.5,
            horizon="1d",
        )
        alert = Alert.from_event(event, self._make_config())
        assert alert.symbol == "AAPL"

    def test_from_event_copies_channels_from_config(self):
        event = PredictionChangedEvent(
            symbol="AAPL",
            old_direction="FLAT",
            new_direction="UP",
            confidence=87.5,
            horizon="1d",
        )
        alert = Alert.from_event(event, self._make_config())
        assert alert.channels == ["email", "discord"]

    def test_from_event_sets_triggered_at(self):
        event = PredictionChangedEvent(
            symbol="AAPL",
            old_direction="FLAT",
            new_direction="UP",
            confidence=87.5,
            horizon="1d",
        )
        alert = Alert.from_event(event, self._make_config())
        assert alert.triggered_at is not None


# ── WatchList ─────────────────────────────────────────────────────────────────


class TestWatchList:
    def _make_watchlist(self) -> WatchList:
        return WatchList(user_id="user-123", name="My Watchlist")

    def test_add_ticker_adds_entry(self):
        wl = self._make_watchlist()
        wl.add_ticker("AAPL")
        assert wl.contains("AAPL") is True

    def test_contains_returns_false_for_missing_symbol(self):
        wl = self._make_watchlist()
        assert wl.contains("AAPL") is False

    def test_remove_ticker_removes_entry(self):
        wl = self._make_watchlist()
        wl.add_ticker("AAPL")
        wl.remove_ticker("AAPL")
        assert wl.contains("AAPL") is False

    def test_remove_ticker_does_nothing_if_not_found(self):
        wl = self._make_watchlist()
        wl.remove_ticker("AAPL")  # should not raise
        assert len(wl.entries) == 0

    def test_add_multiple_tickers(self):
        wl = self._make_watchlist()
        wl.add_ticker("AAPL")
        wl.add_ticker("TSLA")
        assert len(wl.entries) == 2

    def test_entries_defaults_to_empty_list(self):
        wl = self._make_watchlist()
        assert wl.entries == []

    def test_add_ticker_stores_added_at(self):
        wl = self._make_watchlist()
        ts = datetime.now(UTC)
        wl.add_ticker("AAPL", added_at=ts)
        entry = next(e for e in wl.entries if e.symbol == "AAPL")
        assert entry.added_at == ts


# ── APIQuota ──────────────────────────────────────────────────────────────────


class TestAPIQuota:
    def test_is_exceeded_returns_false_when_unlimited(self):
        quota = APIQuota(source_name="newsapi", is_unlimited=True, daily_used=9999)
        assert quota.is_exceeded() is False

    def test_is_exceeded_returns_true_when_daily_at_limit(self):
        quota = APIQuota(source_name="newsapi", daily_limit=100, daily_used=100)
        assert quota.is_exceeded() is True

    def test_is_exceeded_returns_true_when_daily_over_limit(self):
        quota = APIQuota(source_name="newsapi", daily_limit=100, daily_used=101)
        assert quota.is_exceeded() is True

    def test_is_exceeded_returns_false_when_daily_under_limit(self):
        quota = APIQuota(source_name="newsapi", daily_limit=100, daily_used=99)
        assert quota.is_exceeded() is False

    def test_is_exceeded_checks_monthly_when_no_daily_limit(self):
        quota = APIQuota(source_name="newsapi", monthly_limit=1000, monthly_used=1000)
        assert quota.is_exceeded() is True

    def test_is_exceeded_raises_when_no_limits_set(self):
        quota = APIQuota(source_name="newsapi")
        with pytest.raises(ValueError):
            quota.is_exceeded()

    def test_is_low_returns_false_when_unlimited(self):
        quota = APIQuota(source_name="newsapi", is_unlimited=True)
        assert quota.is_low() is False

    def test_is_low_returns_true_when_remaining_at_threshold(self):
        quota = APIQuota(source_name="newsapi", daily_limit=100, daily_used=90, low_threshold=10)
        assert quota.is_low() is True

    def test_is_low_returns_true_when_remaining_below_threshold(self):
        quota = APIQuota(source_name="newsapi", daily_limit=100, daily_used=95, low_threshold=10)
        assert quota.is_low() is True

    def test_is_low_returns_false_when_remaining_above_threshold(self):
        quota = APIQuota(source_name="newsapi", daily_limit=100, daily_used=80, low_threshold=10)
        assert quota.is_low() is False

    def test_percent_used_returns_zero_when_unlimited(self):
        quota = APIQuota(source_name="newsapi", is_unlimited=True)
        assert quota.percent_used() == 0.0

    def test_percent_used_returns_correct_percentage(self):
        quota = APIQuota(source_name="newsapi", daily_limit=100, daily_used=75)
        assert quota.percent_used() == 75.0

    def test_percent_used_returns_100_when_at_limit(self):
        quota = APIQuota(source_name="newsapi", daily_limit=100, daily_used=100)
        assert quota.percent_used() == 100.0

    def test_remaining_returns_none_when_unlimited(self):
        quota = APIQuota(source_name="newsapi", is_unlimited=True)
        assert quota.remaining() is None

    def test_remaining_returns_correct_daily_count(self):
        quota = APIQuota(source_name="newsapi", daily_limit=100, daily_used=60)
        assert quota.remaining() == 40

    def test_remaining_returns_correct_monthly_count(self):
        quota = APIQuota(source_name="newsapi", monthly_limit=1000, monthly_used=600)
        assert quota.remaining() == 400


class TestQuotaStatus:
    def test_quota_status_values_exist(self):
        assert QuotaStatus.OK is not None
        assert QuotaStatus.LOW is not None
        assert QuotaStatus.EXCEEDED is not None


# ── FeatureVector ─────────────────────────────────────────────────────────────


class TestFeatureVector:
    def test_valid_feature_vector_is_created(self):
        fv = FeatureVector(values=[1.0, 2.0, 3.0], schema_version=CURRENT_SCHEMA_VERSION)
        assert len(fv.values) == 3

    def test_raises_for_nan_value(self):
        with pytest.raises(ValueError):
            FeatureVector(values=[1.0, math.nan, 3.0], schema_version=CURRENT_SCHEMA_VERSION)

    def test_raises_for_positive_inf(self):
        with pytest.raises(ValueError):
            FeatureVector(values=[1.0, math.inf, 3.0], schema_version=CURRENT_SCHEMA_VERSION)

    def test_raises_for_negative_inf(self):
        with pytest.raises(ValueError):
            FeatureVector(values=[1.0, -math.inf, 3.0], schema_version=CURRENT_SCHEMA_VERSION)

    def test_raises_for_wrong_schema_version(self):
        with pytest.raises(ValueError):
            FeatureVector(values=[1.0, 2.0], schema_version="0.0")

    def test_empty_values_with_correct_schema_version_is_valid(self):
        fv = FeatureVector(values=[], schema_version=CURRENT_SCHEMA_VERSION)
        assert fv.values == []

    def test_assembled_at_is_set_automatically(self):
        fv = FeatureVector(values=[1.0], schema_version=CURRENT_SCHEMA_VERSION)
        assert fv.assembled_at is not None

    def test_two_instances_have_different_assembled_at(self):
        fv1 = FeatureVector(values=[1.0], schema_version=CURRENT_SCHEMA_VERSION)
        fv2 = FeatureVector(values=[1.0], schema_version=CURRENT_SCHEMA_VERSION)
        # Both should be valid datetimes — timestamps may differ by microseconds
        assert isinstance(fv1.assembled_at, datetime)
        assert isinstance(fv2.assembled_at, datetime)
