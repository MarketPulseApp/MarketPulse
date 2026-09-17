import logging
from typing import Any

import pandas as pd
import ta
from models import OHLCVData

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """
    Service responsible for transforming raw OHLCV market data into engineered feature vectors
    suitable for machine learning models.
    """

    def __init__(self):
        pass

    def generate_features(self, ohlcv_data: list[OHLCVData]) -> dict[str, Any]:
        """
        Convert raw OHLCV domain models into a DataFrame and append technical indicators.

        Args:
            ohlcv_data (List[OHLCVData]): List of domain models representing OHLCV candles.

        Returns:
            Dict[str, Any]: The engineered features as a JSON-serializable dictionary.

        Raises:
            ValueError: If empty data is provided or feature engineering fails.
        """
        if not ohlcv_data:
            raise ValueError("Empty data provided")

        try:
            # Convert domain models to dicts for pandas
            df = pd.DataFrame([candle.model_dump() for candle in ohlcv_data])

            # Ensure required columns exist
            required = {"close", "high", "low", "volume"}
            if not required.issubset(df.columns):
                raise ValueError(f"Missing required columns. Need {required}")

            # Convert columns to float just in case
            for col in required:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            # Handle alternative data
            alt_cols = [
                "put_call_ratio",
                "macro_cpi",
                "stocktwits_sentiment",
                "congressional_buys",
                "insider_buys",
                "insider_sells",
                "reddit_sentiment",
                "rss_sentiment",
            ]
            for col in alt_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                else:
                    df[col] = None
            # Forward fill alternative data as they might be sparse
            df[alt_cols] = df[alt_cols].ffill().fillna(0.0)

            # 1. Momentum Indicator: RSI (Relative Strength Index)
            df["rsi_14"] = ta.momentum.rsi(df["close"], window=14, fillna=True)

            # 2. Trend Indicator: MACD (Moving Average Convergence Divergence)
            macd = ta.trend.MACD(df["close"], fillna=True)
            df["macd"] = macd.macd()
            df["macd_signal"] = macd.macd_signal()
            df["macd_diff"] = macd.macd_diff()

            # 3. Volatility Indicator: Bollinger Bands
            indicator_bb = ta.volatility.BollingerBands(
                close=df["close"], window=20, window_dev=2, fillna=True
            )
            df["bb_bbm"] = indicator_bb.bollinger_mavg()
            df["bb_bbh"] = indicator_bb.bollinger_hband()
            df["bb_bbl"] = indicator_bb.bollinger_lband()

            # 4. Volume Indicator: VWAP (Volume Weighted Average Price) if high/low available
            df["vwap"] = ta.volume.volume_weighted_average_price(
                high=df["high"], low=df["low"], close=df["close"], volume=df["volume"], fillna=True
            )

            # 5. EMA Crossovers (Short and Long term)
            df["ema_9"] = ta.trend.ema_indicator(df["close"], window=9, fillna=True)
            df["ema_21"] = ta.trend.ema_indicator(df["close"], window=21, fillna=True)

            # Return the latest feature vector (the most recent row)
            latest_features = df.iloc[-1].to_dict()

            # Replace NaN with None for JSON serialization
            for k, v in latest_features.items():
                if pd.isna(v):
                    latest_features[k] = None

            return latest_features

        except Exception as e:
            logger.error(f"Feature engineering failed: {str(e)}")
            raise ValueError(f"Feature engineering failed: {str(e)}")

    def generate_features_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Batch process a pandas DataFrame for model training.
        """
        required = {"close", "high", "low", "volume"}
        if not required.issubset(df.columns):
            raise ValueError(f"Missing required columns. Need {required}")

        for col in required:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # Handle alternative data
        alt_cols = [
            "put_call_ratio",
            "macro_cpi",
            "stocktwits_sentiment",
            "congressional_buys",
            "insider_buys",
            "insider_sells",
            "reddit_sentiment",
            "rss_sentiment",
        ]
        for col in alt_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            else:
                df[col] = None
        # Forward fill alternative data as they might be sparse
        df[alt_cols] = df[alt_cols].ffill().fillna(0.0)

        df["rsi_14"] = ta.momentum.rsi(df["close"], window=14, fillna=True)
        macd = ta.trend.MACD(df["close"], fillna=True)
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["macd_diff"] = macd.macd_diff()

        indicator_bb = ta.volatility.BollingerBands(
            close=df["close"], window=20, window_dev=2, fillna=True
        )
        df["bb_bbm"] = indicator_bb.bollinger_mavg()
        df["bb_bbh"] = indicator_bb.bollinger_hband()
        df["bb_bbl"] = indicator_bb.bollinger_lband()

        df["vwap"] = ta.volume.volume_weighted_average_price(
            high=df["high"], low=df["low"], close=df["close"], volume=df["volume"], fillna=True
        )

        df["ema_9"] = ta.trend.ema_indicator(df["close"], window=9, fillna=True)
        df["ema_21"] = ta.trend.ema_indicator(df["close"], window=21, fillna=True)

        return df
