from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass
class HorizonPrediction:
    horizon: Literal["1d", "3d", "7d", "30d"]
    direction: Literal["UP", "FLAT", "DOWN"]
    confidence: float = 0.0
    lstm_confidence: float | None = None
    xgb_confidence: float | None = None
    lgbm_confidence: float | None = None


@dataclass
class Prediction:
    symbol: str
    horizon: Literal["1d", "3d", "7d", "30d"]
    direction: Literal["UP", "FLAT", "DOWN"]
    confidence: float = 0.0
    prediction_time: datetime | None = None
    lstm_direction: str | None = None
    lstm_confidence: float | None = None
    xgb_direction: str | None = None
    xgb_confidence: float | None = None
    lgbm_direction: str | None = None
    lgbm_confidence: float | None = None
    sentiment_score: float | None = None
    anomaly_flag: bool = False

    def is_actionable(self) -> bool:
        return self.confidence >= 75.0


@dataclass
class PredictionOutcome:
    symbol: str
    horizon: str
    prediction_time: datetime
    outcome_time: datetime
    was_correct: bool
    actual_direction: Literal["UP", "FLAT", "DOWN"]
