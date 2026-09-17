from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class FeatureImportance:
    """
    A single feature's contribution to a prediction.

    Used inside PredictionExplanation.features to store SHAP values or
    model-specific importance scores alongside the raw feature value.
    """

    name: str
    value: float  # raw feature value at prediction time
    shap_value: float  # SHAP contribution (positive = pushed toward prediction)
    rank: int = 0  # 1 = most important feature for this prediction


@dataclass
class PredictionExplanation:
    """Human-readable explanation of a single model prediction.

    Generated after inference by a post-hoc explainability step (SHAP,
    LIME, or LLM summarisation). Stored in MongoDB so it can be retrieved
    by the API without re-running the explainer.

    Fields
    ------
    prediction_id
        Foreign key to the predictions table in TimescaleDB.  Use the
        prediction's UUID cast to str.
    symbol
        Ticker symbol the prediction was made for.
    horizon
        Prediction horizon, e.g. "1d", "7d".
    direction
        The predicted direction: "up", "down", or "flat".
    confidence
        Model confidence score in [0, 1].
    features
        List of the top-N feature importances for this prediction.
        Stored as a list of dicts so MongoDB can serialise them without
        knowing about the FeatureImportance class.
    explanation
        LLM-generated plain-English summary of why the model made this
        prediction, referencing the top features.
    model_version
        Version string of the model that produced this prediction.
    created_at
        UTC timestamp when this explanation was generated.
    """

    prediction_id: str
    symbol: str
    horizon: str
    direction: str
    confidence: float
    features: list[dict]  # list of FeatureImportance as plain dicts
    explanation: str
    model_version: str = "v0"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # convenience

    @property
    def top_features(self) -> list[dict]:
        """Return features sorted by abs(shap_value) descending."""
        return sorted(
            self.features,
            key=lambda f: abs(f.get("shap_value", 0.0)),
            reverse=True,
        )

    def to_mongo_doc(self) -> dict:
        return {
            "prediction_id": self.prediction_id,
            "symbol": self.symbol,
            "horizon": self.horizon,
            "direction": self.direction,
            "confidence": self.confidence,
            "features": self.features,
            "explanation": self.explanation,
            "model_version": self.model_version,
            "created_at": self.created_at,
        }

    @classmethod
    def from_mongo_doc(cls, doc: dict) -> PredictionExplanation:
        doc = {k: v for k, v in doc.items() if k != "_id"}
        return cls(**doc)

    @classmethod
    def from_shap(
        cls,
        prediction_id: str,
        symbol: str,
        horizon: str,
        direction: str,
        confidence: float,
        shap_values: dict[str, tuple[float, float]],
        explanation: str,
        model_version: str = "v0",
        top_n: int = 10,
    ) -> PredictionExplanation:
        """Construct from a dict of {feature_name: (raw_value, shap_value)}.

        This is a convenience constructor for use directly after a SHAP
        explainer run:

            shap_values = {
                "rsi_14":      (62.3,  0.045),
                "volume_ratio": (1.8,  0.031),
                ...
            }
            exp = PredictionExplanation.from_shap(
                prediction_id=pred.id,
                symbol="AAPL",
                horizon="1d",
                direction=pred.direction,
                confidence=pred.confidence,
                shap_values=shap_values,
                explanation="Model is bullish primarily due to elevated RSI...",
            )
        """
        sorted_features = sorted(
            shap_values.items(),
            key=lambda item: abs(item[1][1]),
            reverse=True,
        )[:top_n]

        features = [
            {
                "name": name,
                "value": vals[0],
                "shap_value": vals[1],
                "rank": rank + 1,
            }
            for rank, (name, vals) in enumerate(sorted_features)
        ]

        return cls(
            prediction_id=prediction_id,
            symbol=symbol,
            horizon=horizon,
            direction=direction,
            confidence=confidence,
            features=features,
            explanation=explanation,
            model_version=model_version,
        )
