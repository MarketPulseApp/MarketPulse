"""
Presentation layer CLI for testing Zero-Loss strategy constraints.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data_access.loader import MarketDataLoader
from logic.backtester import Backtester
from logic.risk_manager import RiskManager
from logic.strategy import MLStrategy

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def main():
    print("Initializing Backtester Engine for Zero-Loss Strategy...")

    loader = MarketDataLoader()
    # We use simulate_local=True which has the simulated confidence and anomaly detection logic
    # In reality, it would hit the updated ML sidecar endpoint.
    strategy = MLStrategy(simulate_local=True)

    # We'll also use RiskManager to prevent any large drawdowns.
    risk_manager = RiskManager(
        max_drawdown_pct=0.01, max_daily_loss_pct=0.01, risk_per_trade_pct=0.01
    )

    engine = Backtester(
        data_loader=loader, strategy=strategy, risk_manager=risk_manager, initial_capital=10000.0
    )

    start_time = datetime(2023, 1, 1, 9, 30, 0)

    print("Running Backtest Phase 3: Zero-Loss / Near Zero-Loss...")
    results = await engine.run(symbol="SPY", start_time=start_time, periods=100)

    print("\n--- Zero-Loss Strategy Test Results ---")
    print(f"Initial Value : ${results['initial_value']:.2f}")
    print(f"Final Value   : ${results['final_value']:.2f}")
    print(f"Net Profit    : ${results['net_profit']:.2f}")
    print(f"Return        : {results['return_pct']:.2f}%")
    print(f"Total Trades  : {results['total_trades']}")
    print(f"Was Halted    : {results['halted']}")
    print(f"Halt Reason   : {results['halt_reason']}")


if __name__ == "__main__":
    asyncio.run(main())
