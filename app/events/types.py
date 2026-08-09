"""
Every event is serialized with MessagePack in app/events/publisher.py - keep all field
types to primitives (str, int, float, bool) except timestamp which is converted to
an ISO string before packing. datetime fields are typed datetime | None for optimal
timestamp injection
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class BaseEvent:
    event_type: str
    timestamp: datetime | None = None


@dataclass
class PredictionChangedEvent(BaseEvent):
    """
    ML model direction flip for a ticker on a given horizon.
    """

    event_type: str = field(default="prediction_changed", init=False)
    symbol: str = ""
    old_direction: str = ""  # "UP" | "FLAT" | "DOWN"
    new_direction: str = ""  # "UP" | "FLAT" | "DOWN"
    confidence: float = 0.0  # 0.0 - 100.0
    horizon: str = ""  # "1d" | "3d" | "7d" | "30d"


@dataclass
class UnusualVolumeEvent(BaseEvent):
    """
    Trading volume is significantly above the rolling average.
    """

    event_type: str = field(default="unusual_volume", init=False)
    symbol: str = ""
    volume: int = 0  # current bar volume
    avg_volume: int = 0  # rolling average volume
    multiplier: float = 0.0  # volume | avg_volume


@dataclass
class BreakingNewsEvent(BaseEvent):
    """
    High-impact news article with significant FinBERT sentiment.
    """

    event_type: str = field(default="breaking_news", init=False)
    symbol: str = ""
    headline: str = ""
    source: str = ""
    finbert_score: float = 0.0  # -1.0 (bearish) to +1.0 (bullish)
    url: str = ""


# If all channels failed, publishes ApplicationErrorEvent
@dataclass
class ApplicationErrorEvent(BaseEvent):
    """
    All delivery channels failed, or an unhandled exception occured in a module.
    """

    event_type: str = field(default="application_error", init=False)
    module: str = ""  # e.g. "ingestion.newsapi", "delivery.email"
    error_message: str = ""
    traceback: str = ""  # formatted traceback string; empty if unavailable


#  Send quota warning alerts when any source approaches its limit
@dataclass
class QuotaWarningEvent(BaseEvent):
    """
    An API source is approaching its daily or monthly call limit.
    """

    event_type: str = field(default="quota_warning", init=False)
    source_name: str = ""  # e.g. "newsapi", "alpha_vantage", "gnews"
    quota_type: str = ""  # "daily" | "monthly"
    current_count: int = 0
    limit: int = 0
    percent_used: float = 0.0  # 0.0 - 100.0
    resets_at: datetime | None = None


# Send earnings-approaching alerts when configured
@dataclass
class EarningsApproachingEvent(BaseEvent):
    """
    An earnings announcment is within the user-configured look-ahead window
    """

    event_type: str = field(default="earnings_approaching", init=False)
    symbol: str = ""
    report_date: datetime | None = None
    days_until: int = 0
    estimate_eps: float | None = None  # None if not yet published
    prev_eps: float | None = None  # previous quarter actual EPS


# SEC Form 4 filing tracker; Neo4j INSIDER_BOUGHT / INSIDER_SOLD edges
@dataclass
class InsiderTradeEvent(BaseEvent):
    """
    A new SEC Form 4 insider buy or sell filing was detected
    """

    event_type: str = field(default="insider_trade", init=False)
    symbol: str = ""
    insider_name: str = ""
    title: str = ""  # e.g. "CEO", "CFO", "Director"
    trade_type: str = ""  # "buy" | "sell"
    shares: int = 0
    price_per_share: float = 0.0
    total_value: float = 0.0  # shares * price_per_share
    filing_date: datetime | None = None


# RSI(14) is computed for every ticker; overbought/oversold are standard user thresholds.
@dataclass
class RsiThresholdCrossedEvent(BaseEvent):
    """
    RSI crossed above the overbought threshold or below the oversold threshold
    """

    event_type: str = field(default="rsi_threshold_crossed", init=False)
    symbol: str = ""
    rsi_value: float = 0.0
    threshold: float = 0.0  # typically 70.0 (overbought) or 30.0 (oversold)
    condition: str = ""  # "overbought" | "oversold"


# SMA(20/50/200) overlays are shown on every chart; price crossing a moving average
# is a configurable alert threshold in the gear panel.
@dataclass
class PriceCrossedSMAEvent(BaseEvent):
    """
    Price crossed above or below a simple moving average
    """

    event_type: str = field(default="price_crossed_sma", init=False)
    symbol: str = ""
    price: float = 0.0
    sma_period: int = 0
    sma_value: float = 0.0
    cross_direction: str = ""


# The feature vector tracks a 7-day sentiment trend via linear regression slope.
# A significant shift in that slope is a configurable alert.
@dataclass
class SentimentShiftedEvent(BaseEvent):
    """
    The 7-day sentiment trend for a ticker shifted significantly
    """

    event_type: str = field(default="sentiment_shifted", init=False)
    symbol: str = ""
    previous_score: float = 0.0  # score at start of window
    current_score: float = 0.0  # score at end of window
    delta: float = 0.0  # current_score - previous_score
    window_days: int = 7
    source: str = ""  # "news" | "reddit" | "combined"


# The SQLite event journal explicitly records "every prediction, alert, and training run".
@dataclass
class ModelRetainedEvent(BaseEvent):
    """
    The ML ensemble completed a retraining run
    """

    event_type: str = field(default="model_retrained", init=False)
    model_version: str = ""  # e.g. "ensemble-v4"
    previous_version: str = ""  # e.g. "ensemble-v3"
    accuracy_delta: float = 0.0  # new_accuracy - previous_accuracy (can be negative)
    training_duration_seconds: float = 0.0
    ticker_count: int = 0  # number of tickers retrained on
    timestamp: datetime | None = None


# The predictions table has was_correct and outcome_time fields; once the horizon
# window closes the outcome is evaluated and this event is published.
@dataclass
class PredictionOutcomeResolvedEvent(BaseEvent):
    """
    A prediction's horizon window closed and the outcome has been evaluated.
    """

    event_type: str = field(default="prediction_outcome_resolved", init=False)
    symbol: str = ""
    horizon: str = ""  # "1d" | "3d" | "7d" | "30d"
    predicted_direction: str = ""  # "UP" | "FLAT" | "DOWN"
    actual_direction: str = ""  # "UP" | "FLAT" | "DOWN"
    was_correct: bool = False
    confidence: float = 0.0


# Used by the consumer to deserialize raw MessagePack dicts back into typed objects.
ALL_EVENT_TYPES: dict[str, type] = {
    "prediction_changed": PredictionChangedEvent,
    "unusual_volume": UnusualVolumeEvent,
    "breaking_news": BreakingNewsEvent,
    "application_error": ApplicationErrorEvent,
    "quota_warning": QuotaWarningEvent,
    "earnings_approaching": EarningsApproachingEvent,
    "insider_trade": InsiderTradeEvent,
    "rsi_threshold_crossed": RsiThresholdCrossedEvent,
    "price_crossed_sma": PriceCrossedSMAEvent,
    "sentiment_shifted": SentimentShiftedEvent,
    "model_retrained": ModelRetainedEvent,
    "prediction_outcome_resolved": PredictionOutcomeResolvedEvent,
}
