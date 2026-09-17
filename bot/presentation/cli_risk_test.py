"""
Presentation layer CLI for testing Risk Management.
Forces bad trades or injects bad data to verify the risk manager halts trading.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data_access.loader import MarketDataLoader
from domain.models import MarketData
from logic.backtester import Backtester
from logic.risk_manager import RiskManager
from logic.strategy import MLStrategy

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class BadStrategy(MLStrategy):
    """A strategy designed to lose money to test the risk manager."""

    async def get_signal(self, current_data: MarketData) -> str:
        # Just always buy, as the market is crashing.
        return "BUY"


class BadDataLoader(MarketDataLoader):
    """Generates market data that strictly crashes to trigger drawdown limit."""

    def load_historical_data(self, symbol: str, start_time: datetime, periods: int = 100):
        data = []
        current_time = start_time
        base_price = 100.0

        for i in range(periods):
            # Price drops 1% every period!
            open_p = base_price
            close_p = open_p * 0.99
            high_p = open_p
            low_p = close_p

            candle = MarketData(
                timestamp=current_time,
                symbol=symbol,
                open_price=round(open_p, 2),
                high_price=round(high_p, 2),
                low_price=round(low_p, 2),
                close_price=round(close_p, 2),
                volume=1000.0,
            )
            data.append(candle)

            base_price = close_p
            from datetime import timedelta

            current_time += timedelta(minutes=1)

        return data


async def main():
    print("Initializing Backtester Engine with Risk Manager...")

    loader = BadDataLoader()
    strategy = BadStrategy(simulate_local=True)
    # Set max drawdown to 5% and max daily loss to 2%
    risk_manager = RiskManager(
        max_drawdown_pct=0.05, max_daily_loss_pct=0.02, risk_per_trade_pct=0.1
    )

    engine = Backtester(
        data_loader=loader, strategy=strategy, risk_manager=risk_manager, initial_capital=10000.0
    )

    start_time = datetime(2023, 1, 1, 9, 30, 0)

    print("Running Backtest Phase 2: Risk Management...")
    results = await engine.run(symbol="CRASH", start_time=start_time, periods=100)

    print("\n--- Risk Management Test Results ---")
    print(f"Initial Value : ${results['initial_value']:.2f}")
    print(f"Final Value   : ${results['final_value']:.2f}")
    print(f"Net Profit    : ${results['net_profit']:.2f}")
    print(f"Return        : {results['return_pct']:.2f}%")
    print(f"Total Trades  : {results['total_trades']}")
    print(f"Was Halted    : {results['halted']}")
    print(f"Halt Reason   : {results['halt_reason']}")


if __name__ == "__main__":
    asyncio.run(main())
