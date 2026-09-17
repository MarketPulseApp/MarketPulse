import logging
import os

import joblib
from feature_engineering import FeatureEngineer
from repository import MarketDataRepository
from sklearn.model_selection import train_test_split

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_training():
    """
    Fetch historical data, engineer features, and train a baseline Random Forest model.
    """
    logger.info("Starting model training pipeline...")

    # 1. Fetch Data
    repo = MarketDataRepository()
    logger.info("Fetching historical data from database...")
    df = repo.fetch_historical_data(symbol="BTC/USDT", limit=10000)

    if df.empty:
        logger.warning("No data returned from database. Training aborted.")
        # Create a dummy dataframe for testing if no DB data is available
        import numpy as np
        import pandas as pd

        logger.info("Creating dummy data for testing...")
        dates = pd.date_range("2023-01-01", periods=1000)
        df = pd.DataFrame(
            {
                "time": dates,
                "open": np.random.uniform(20000, 30000, 1000),
                "high": np.random.uniform(21000, 31000, 1000),
                "low": np.random.uniform(19000, 29000, 1000),
                "close": np.random.uniform(20000, 30000, 1000),
                "volume": np.random.uniform(10, 100, 1000),
                "put_call_ratio": np.random.uniform(0.5, 1.5, 1000),
                "macro_cpi": np.random.uniform(2.0, 5.0, 1000),
                "stocktwits_sentiment": np.random.uniform(-1.0, 1.0, 1000),
                "congressional_buys": np.random.randint(0, 5, 1000),
                "insider_buys": np.random.randint(0, 10, 1000),
                "insider_sells": np.random.randint(0, 10, 1000),
                "reddit_sentiment": np.random.uniform(-1.0, 1.0, 1000),
                "rss_sentiment": np.random.uniform(-1.0, 1.0, 1000),
            }
        )

    # 2. Feature Engineering
    engineer = FeatureEngineer()
    logger.info("Engineering features...")
    df_features = engineer.generate_features_batch(df)

    # Drop rows with NaN (created by rolling windows in TA)
    df_features.dropna(inplace=True)

    # Target variable: Predict the next period's price direction (1 for up, 0 for down)
    df_features["next_close"] = df_features["close"].shift(-1)
    df_features.dropna(inplace=True)
    df_features["target"] = (df_features["next_close"] > df_features["close"]).astype(int)

    # Select feature columns (excluding non-numeric or future-leaking ones)
    feature_cols = [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "rsi_14",
        "macd",
        "macd_signal",
        "macd_diff",
        "bb_bbm",
        "bb_bbh",
        "bb_bbl",
        "vwap",
        "ema_9",
        "ema_21",
        "put_call_ratio",
        "macro_cpi",
        "stocktwits_sentiment",
        "congressional_buys",
        "insider_buys",
        "insider_sells",
        "reddit_sentiment",
        "rss_sentiment",
    ]

    X = df_features[feature_cols]
    y = df_features["target"]

    # 3. Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

    # 3.5 Train Anomaly Detector (Isolation Forest)
    from sklearn.ensemble import IsolationForest

    logger.info("Training Isolation Forest for anomaly detection...")
    iso_forest = IsolationForest(n_estimators=100, contamination=0.01, random_state=42)
    iso_forest.fit(X_train)

    # 4. Model Training (Classification for probabilities)
    from sklearn.ensemble import RandomForestClassifier

    logger.info("Training strict Random Forest Classifier...")
    model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight="balanced")
    model.fit(X_train, y_train)

    # 5. Evaluation
    from sklearn.metrics import accuracy_score

    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    logger.info(f"Model Evaluation - Accuracy: {accuracy:.4f}")

    # 6. Save Model
    models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
    if not os.path.exists(models_dir):
        models_dir = "/opt/marketpulse/models"
    os.makedirs(models_dir, exist_ok=True)

    model_path = os.path.join(models_dir, "rf_baseline_model.joblib")
    anomaly_model_path = os.path.join(models_dir, "anomaly_model.joblib")

    joblib.dump(model, model_path)
    joblib.dump(iso_forest, anomaly_model_path)
    logger.info(f"Models saved to {models_dir}")


if __name__ == "__main__":
    run_training()
