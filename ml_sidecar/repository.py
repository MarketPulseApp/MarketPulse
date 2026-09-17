import logging
import os

import pandas as pd
from sqlalchemy import create_engine

logger = logging.getLogger(__name__)


class MarketDataRepository:
    """
    Data Access layer for fetching historical market data from the database.
    """

    def __init__(self):
        # Default to the node-123 URL if POSTGRES_URL isn't set, but generally expect it in env
        self.db_url = os.environ.get(
            "POSTGRES_URL",
            "postgresql://marketpulse:marketpulse_password_1122@192.168.1.123:5432/marketpulse",
        )
        try:
            self.engine = create_engine(self.db_url)
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            raise

    def fetch_historical_data(self, symbol: str = "BTC/USDT", limit: int = 10000) -> pd.DataFrame:
        """
        Fetch historical OHLCV data and merge with alternative data sources.
        """
        ohlcv_query = """
            SELECT time, open, high, low, close, volume 
            FROM market_data 
            WHERE symbol = %(symbol)s 
            ORDER BY time ASC 
            LIMIT %(limit)s
        """
        alt_query = """
            SELECT time, 
                   put_call_ratio, 
                   macro_cpi, 
                   stocktwits_sentiment, 
                   congressional_buys,
                   insider_buys,
                   insider_sells,
                   reddit_sentiment,
                   rss_sentiment
            FROM alt_data_view
            WHERE symbol = %(symbol)s
            ORDER BY time ASC
            LIMIT %(limit)s
        """
        try:
            df_ohlcv = pd.read_sql(
                ohlcv_query, self.engine, params={"symbol": symbol, "limit": limit}
            )
            if not df_ohlcv.empty:
                df_ohlcv.sort_values("time", inplace=True)

                # Attempt to fetch alternative data
                try:
                    df_alt = pd.read_sql(
                        alt_query, self.engine, params={"symbol": symbol, "limit": limit}
                    )
                    if not df_alt.empty:
                        df_alt.sort_values("time", inplace=True)
                        # Merge on time using merge_asof for time series alignment
                        df_ohlcv = pd.merge_asof(df_ohlcv, df_alt, on="time", direction="backward")
                except Exception as e:
                    logger.warning(
                        f"Failed to fetch alternative data, proceeding with OHLCV only: {e}"
                    )

                df_ohlcv.reset_index(drop=True, inplace=True)
            return df_ohlcv
        except Exception as e:
            logger.error(f"Failed to fetch historical data: {e}")
            return pd.DataFrame()
