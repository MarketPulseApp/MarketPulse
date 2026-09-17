"""
Logic layer for trading strategies.
"""

import logging

import httpx
from domain.models import MarketData

logger = logging.getLogger(__name__)


class MLStrategy:
    """Trading strategy powered by an external ML model."""

    def __init__(
        self, api_url: str = "http://192.168.1.134:8085/predict", simulate_local: bool = True
    ):
        """
        Initialize the strategy.

        Args:
            api_url (str): Endpoint for the ML prediction service.
            simulate_local (bool): If True, use a simulated local prediction instead of network calls.
        """
        self.api_url = api_url
        self.simulate_local = simulate_local

    async def get_signal(
        self,
        current_data: MarketData,
        confidence_threshold: float = 0.999,
        active_strategy: str = "default",
    ) -> str:
        """
        Get trading signal ('BUY', 'SELL', 'HOLD') for current market data.

        Args:
            current_data (MarketData): The latest market candle.
            confidence_threshold (float): Minimum confidence to trigger trade.
            active_strategy (str): Strategy variant to use.

        Returns:
            str: Trading action to take.
        """
        if self.simulate_local:
            # Simulate prediction based on price momentum with a "zero-loss" logic mock
            # In simulation, we just randomly return HOLD to simulate low confidence
            import random

            is_anomaly = random.random() < 0.05
            confidence = random.uniform(0.95, 1.0)

            if is_anomaly:
                logger.info("Simulated anomaly detected. Holding.")
                return "HOLD"

            if confidence < confidence_threshold:
                logger.info(
                    f"Simulated confidence {confidence:.4f} < {confidence_threshold:.3f}. Holding."
                )
                return "HOLD"

            # Adjust entry criteria to ensure expected gross profit massively outweighs slippage
            price_change = (
                current_data.close_price - current_data.open_price
            ) / current_data.open_price

            if price_change > 0.02:
                return "BUY"
            elif price_change < -0.02:
                return "SELL"
            else:
                return "HOLD"

        # Real network call to ML sidecar
        try:
            payload = {
                "data": [
                    {
                        "time": current_data.timestamp.isoformat(),
                        "open": current_data.open_price,
                        "high": current_data.high_price,
                        "low": current_data.low_price,
                        "close": current_data.close_price,
                        "volume": current_data.volume,
                    }
                ]
            }
            async with httpx.AsyncClient() as client:
                resp = await client.post(self.api_url, json=payload, timeout=2.0)
                if resp.status_code == 200:
                    data = resp.json()
                    is_anomaly = data.get("is_anomaly", False)
                    confidence = data.get("confidence", 0.0)
                    signal = data.get("signal", "HOLD").upper()

                    if is_anomaly:
                        logger.warning(
                            f"Anomaly detected by ML pipeline for {current_data.symbol}. Holding position."
                        )
                        return "HOLD"

                    if confidence < confidence_threshold:
                        logger.info(
                            f"Signal {signal} confidence {confidence:.4f} is below {confidence_threshold:.3f} threshold. Holding."
                        )
                        return "HOLD"

                    return signal
                else:
                    logger.warning(f"ML sidecar returned status {resp.status_code}: {resp.text}")
                    return "HOLD"
        except Exception as e:
            logger.error(f"Failed to fetch ML prediction: {e}")
            return "HOLD"
