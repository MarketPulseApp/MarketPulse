from __future__ import annotations

from datetime import datetime

from domain.explanation import FeatureImportance, PredictionExplanation


def make_explanation(**kwargs) -> PredictionExplanation:
    defaults = dict(
        prediction_id="pred-001",
        symbol="AAPL",
        horizon="1d",
        direction="up",
        confidence=0.75,
        features=[
            {"name": "rsi_14", "value": 62.3, "shap_value": 0.045, "rank": 1},
            {"name": "volume_ratio", "value": 1.8, "shap_value": -0.031, "rank": 2},
            {"name": "macd", "value": 0.5, "shap_value": 0.020, "rank": 3},
        ],
        explanation="Model is bullish due to elevated RSI.",
    )
    defaults.update(kwargs)
    return PredictionExplanation(**defaults)


# ── FeatureImportance ─────────────────────────────────────────────────────────


def test_feature_importance_construction():
    fi = FeatureImportance(name="rsi_14", value=62.3, shap_value=0.045, rank=1)
    assert fi.name == "rsi_14"
    assert fi.rank == 1


def test_feature_importance_default_rank():
    fi = FeatureImportance(name="x", value=1.0, shap_value=0.1)
    assert fi.rank == 0


# ── PredictionExplanation ─────────────────────────────────────────────────────


def test_minimal_construction():
    e = make_explanation()
    assert e.prediction_id == "pred-001"
    assert e.model_version == "v0"
    assert isinstance(e.created_at, datetime)


def test_top_features_sorted_by_abs_shap():
    e = make_explanation()
    top = e.top_features
    shap_vals = [abs(f["shap_value"]) for f in top]
    assert shap_vals == sorted(shap_vals, reverse=True)


def test_top_features_handles_negative_shap():
    e = make_explanation(
        features=[
            {"name": "a", "value": 1.0, "shap_value": -0.9, "rank": 1},
            {"name": "b", "value": 2.0, "shap_value": 0.1, "rank": 2},
        ]
    )
    assert e.top_features[0]["name"] == "a"


# ── to_mongo_doc / from_mongo_doc ─────────────────────────────────────────────


def test_to_mongo_doc_keys():
    doc = make_explanation().to_mongo_doc()
    for key in (
        "prediction_id",
        "symbol",
        "horizon",
        "direction",
        "confidence",
        "features",
        "explanation",
        "model_version",
        "created_at",
    ):
        assert key in doc


def test_from_mongo_doc_drops_id():
    doc = make_explanation().to_mongo_doc()
    doc["_id"] = "mongo-id"
    e = PredictionExplanation.from_mongo_doc(doc)
    assert e.prediction_id == "pred-001"


def test_from_mongo_doc_roundtrip():
    original = make_explanation(model_version="v2")
    restored = PredictionExplanation.from_mongo_doc(original.to_mongo_doc())
    assert restored.prediction_id == original.prediction_id
    assert restored.model_version == "v2"
    assert len(restored.features) == 3


# ── from_shap ─────────────────────────────────────────────────────────────────


def test_from_shap_basic():
    shap_values = {
        "rsi_14": (62.3, 0.045),
        "volume_ratio": (1.8, 0.031),
        "macd": (0.5, 0.010),
    }
    e = PredictionExplanation.from_shap(
        prediction_id="pred-002",
        symbol="MSFT",
        horizon="7d",
        direction="down",
        confidence=0.6,
        shap_values=shap_values,
        explanation="Bearish signal",
    )
    assert e.prediction_id == "pred-002"
    assert len(e.features) == 3
    assert e.features[0]["name"] == "rsi_14"
    assert e.features[0]["rank"] == 1


def test_from_shap_top_n_limits():
    shap_values = {f"feat_{i}": (float(i), float(i) * 0.01) for i in range(20)}
    e = PredictionExplanation.from_shap(
        prediction_id="x",
        symbol="X",
        horizon="1d",
        direction="up",
        confidence=0.5,
        shap_values=shap_values,
        explanation="test",
        top_n=5,
    )
    assert len(e.features) == 5


def test_from_shap_sorts_by_abs_shap():
    shap_values = {
        "small": (1.0, 0.01),
        "large": (2.0, -0.99),
    }
    e = PredictionExplanation.from_shap(
        prediction_id="y",
        symbol="Y",
        horizon="1d",
        direction="up",
        confidence=0.5,
        shap_values=shap_values,
        explanation="test",
    )
    assert e.features[0]["name"] == "large"
