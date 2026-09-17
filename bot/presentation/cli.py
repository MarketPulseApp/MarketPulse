"""
Presentation layer CLI for running backtests manually.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Ensure the root bot directory is in the path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data_access.loader import MarketDataLoader
from logic.backtester import Backtester
from logic.strategy import MLStrategy

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def main():
    print("Initializing Backtester Engine...")

    loader = MarketDataLoader()
    # For initial testing, we use simulate_local=True.
    # To test the real network connection to ML sidecar, change this to False
    # provided the sidecar is accessible.
    strategy = MLStrategy(simulate_local=True)
    engine = Backtester(data_loader=loader, strategy=strategy, initial_capital=10000.0)

    start_time = datetime(2023, 1, 1, 9, 30, 0)

    print("Running Backtest Phase 1...")
    results = await engine.run(symbol="AAPL", start_time=start_time, periods=1000)

    print("\n--- Backtest Results ---")
    print(f"Initial Value : ${results['initial_value']:.2f}")
    print(f"Final Value   : ${results['final_value']:.2f}")
    print(f"Net Profit    : ${results['net_profit']:.2f}")
    print(f"Return        : {results['return_pct']:.2f}%")
    print(f"Total Trades  : {results['total_trades']}")


if __name__ == "__main__":
    asyncio.run(main())
