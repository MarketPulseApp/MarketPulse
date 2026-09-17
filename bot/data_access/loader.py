"""
Data Access layer for loading historical market data.
"""

import random
from datetime import datetime, timedelta

from domain.models import MarketData


class MarketDataLoader:
    """Loads historical market data for backtesting."""

    def __init__(self, data_path: str = None):
        """
        Initialize the loader.

        Args:
            data_path (str): Optional path to a data source (e.g., CSV file).
        """
        self.data_path = data_path

    def load_historical_data(
        self, symbol: str, start_time: datetime, periods: int = 100
    ) -> list[MarketData]:
        """
        Load historical market data.
        For now, generates synthetic dummy data for testing purposes.

        Args:
            symbol (str): The ticker symbol to load.
            start_time (datetime): The start datetime.
            periods (int): Number of periods (candles) to generate/load.

        Returns:
            List[MarketData]: A list of MarketData objects ordered by time.
        """
        data = []
        current_time = start_time
        base_price = 100.0

        for _ in range(periods):
            # Generate somewhat random walk data
            open_p = base_price
            close_p = open_p + random.uniform(-1.0, 1.2)  # Slight upward bias for testing
            high_p = max(open_p, close_p) + random.uniform(0.0, 0.5)
            low_p = min(open_p, close_p) - random.uniform(0.0, 0.5)
            vol = random.uniform(1000, 5000)

            candle = MarketData(
                timestamp=current_time,
                symbol=symbol,
                open_price=round(open_p, 2),
                high_price=round(high_p, 2),
                low_price=round(low_p, 2),
                close_price=round(close_p, 2),
                volume=round(vol, 2),
            )
            data.append(candle)

            # Update state for next candle
            base_price = close_p
            current_time += timedelta(minutes=1)

        return data
