import asyncio
import logging
from datetime import datetime, timedelta

from data_access.loader import MarketDataLoader
from logic.backtester import Backtester
from logic.risk_manager import RiskManager
from logic.strategy import MLStrategy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run():
    logger.info("Initializing Zero-Loss Strategy Backtest")

    # Mock data loader
    data_loader = MarketDataLoader()

    # ML Strategy pointing to our sidecar
    # Ensure this URL matches the sidecar endpoint
    strategy = MLStrategy(api_url="http://192.168.1.134:8085/predict", simulate_local=False)

    # Optional Risk Manager
    risk_manager = RiskManager()

    backtester = Backtester(
        data_loader=data_loader,
        strategy=strategy,
        risk_manager=risk_manager,
        initial_capital=10000.0,
    )

    start_time = datetime.utcnow() - timedelta(days=30)

    # Run backtest for BTC/USDT over 50 periods
    metrics = await backtester.run(symbol="BTC/USDT", start_time=start_time, periods=50)

    print("\n" + "=" * 50)
    print("BACKTEST RESULTS (Zero-Loss Constraint Enabled)")
    print("=" * 50)
    for k, v in metrics.items():
        print(f"{k}: {v}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(run())
