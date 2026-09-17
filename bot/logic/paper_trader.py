"""
Logic layer for live internal paper trading.
"""

import asyncio
import logging
import os
from datetime import datetime

import asyncpg
from domain.models import MarketData, Portfolio, Trade
from logic.risk_manager import RiskManager
from logic.strategy import MLStrategy

logger = logging.getLogger(__name__)


class PaperTrader:
    def __init__(self):
        # Fallback to local node-123 if not set
        self.db_url = os.getenv(
            "POSTGRES_URL",
            "postgresql://marketpulse:marketpulse_password_1122@192.168.1.123:5432/marketpulse",
        )
        self.pool = None

        # Zero-loss criteria strategy. simulate_local=False queries real ml_sidecar.
        ml_url = os.getenv("MARKETPULSE_ML_URL", "http://marketpulse-ml-sidecar:8085/predict")
        self.strategy = MLStrategy(api_url=ml_url, simulate_local=False)

        # Risk thresholds
        self.risk_manager = RiskManager(
            max_drawdown_pct=0.01, max_daily_loss_pct=0.01, risk_per_trade_pct=0.01
        )
        self.portfolio = Portfolio(initial_cash=10000.0)

        self.symbol = "BTC/USDT"
        self.last_candle_time = None
        self.is_running = False

    async def init_db(self):
        logger.info(f"Connecting to Database at {self.db_url}...")
        self.pool = await asyncpg.create_pool(self.db_url)

        async with self.pool.acquire() as conn:
            # Create paper trading tables
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS paper_portfolio (
                    id SERIAL PRIMARY KEY,
                    cash DOUBLE PRECISION,
                    updated_at TIMESTAMP
                );
            """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS paper_trades (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(50),
                    action VARCHAR(10),
                    quantity DOUBLE PRECISION,
                    price DOUBLE PRECISION,
                    timestamp TIMESTAMP
                );
            """
            )

            # Load initial or latest portfolio cash
            row = await conn.fetchrow("SELECT cash FROM paper_portfolio ORDER BY id DESC LIMIT 1")
            if row:
                self.portfolio.cash = row["cash"]
                logger.info(f"Loaded portfolio cash: ${self.portfolio.cash:.2f}")
            else:
                await conn.execute(
                    "INSERT INTO paper_portfolio (cash, updated_at) VALUES ($1, $2)",
                    self.portfolio.cash,
                    datetime.utcnow(),
                )

    async def save_trade(self, trade: Trade):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO paper_trades (symbol, action, quantity, price, timestamp) VALUES ($1, $2, $3, $4, $5)",
                trade.symbol,
                trade.action,
                trade.quantity,
                trade.price,
                trade.timestamp,
            )
            await conn.execute(
                "INSERT INTO paper_portfolio (cash, updated_at) VALUES ($1, $2)",
                self.portfolio.cash,
                datetime.utcnow(),
            )

    async def get_latest_market_data(self) -> MarketData:
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT time as timestamp, symbol, open, high, low, close, volume 
                    FROM ohlcv 
                    WHERE symbol = $1 
                    ORDER BY time DESC LIMIT 1
                """,
                    self.symbol,
                )

                if row:
                    return MarketData(
                        timestamp=row["timestamp"],
                        symbol=row["symbol"],
                        open_price=float(row["open"]),
                        high_price=float(row["high"]),
                        low_price=float(row["low"]),
                        close_price=float(row["close"]),
                        volume=float(row["volume"]),
                    )
        except Exception as e:
            logger.error(f"Failed to fetch live market data: {e}")
        return None

    async def get_system_settings(self):
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT active_strategy, confidence_threshold FROM system_settings WHERE id = 1"
                )
                if row:
                    return row["active_strategy"], float(row["confidence_threshold"])
        except Exception as e:
            logger.error(f"Failed to fetch system settings: {e}")
        return "default", 0.999

    async def start(self):
        self.is_running = True
        await self.init_db()
        logger.info("Live Internal Paper Trading Engine started.")

        while self.is_running:
            try:
                candle = await self.get_latest_market_data()
                if candle and candle.timestamp != self.last_candle_time:
                    self.last_candle_time = candle.timestamp
                    await self.process_candle(candle)

            except Exception as e:
                logger.error(f"Error in paper trader loop: {e}")

            # Poll every 5 seconds for new live data
            await asyncio.sleep(5)

    async def process_candle(self, candle: MarketData):
        logger.info(f"Live Market Update at {candle.timestamp}: close {candle.close_price:.2f}")

        current_prices = {self.symbol: candle.close_price}
        portfolio_value = self.portfolio.get_total_value(current_prices)
        self.risk_manager.update_state(candle.timestamp, portfolio_value)

        if self.risk_manager.is_halted:
            logger.warning(f"Paper Trading halted: {self.risk_manager.halt_reason}")
            # Liquidate open positions
            for sym, pos in list(self.portfolio.positions.items()):
                if pos.quantity > 0:
                    trade = Trade(
                        timestamp=candle.timestamp,
                        symbol=sym,
                        quantity=pos.quantity,
                        price=candle.close_price,
                        action="SELL",
                    )
                    self.portfolio.add_trade(trade)
                    await self.save_trade(trade)
                    logger.info(f"LIQUIDATED {sym} position due to Risk Halt.")
            return

        active_strategy, confidence_threshold = await self.get_system_settings()
        signal = await self.strategy.get_signal(
            candle, confidence_threshold=confidence_threshold, active_strategy=active_strategy
        )

        trade_qty = 1.0

        if signal == "BUY":
            allowed, qty = self.risk_manager.vet_order(
                "BUY", candle.close_price, self.portfolio, current_prices
            )
            if allowed:
                trade_qty = qty
                cost = trade_qty * candle.close_price
                if self.portfolio.cash >= cost:
                    trade = Trade(
                        timestamp=candle.timestamp,
                        symbol=self.symbol,
                        quantity=trade_qty,
                        price=candle.close_price,
                        action="BUY",
                    )
                    self.portfolio.add_trade(trade)
                    await self.save_trade(trade)
                    logger.info(f"LIVE PAPER TRADE: BUY {trade_qty} at {candle.close_price}")

        elif signal == "SELL":
            pos = self.portfolio.positions.get(self.symbol)
            if pos and pos.quantity > 0:
                allowed, _ = self.risk_manager.vet_order(
                    "SELL", candle.close_price, self.portfolio, current_prices
                )
                if allowed:
                    trade_qty = pos.quantity
                    trade = Trade(
                        timestamp=candle.timestamp,
                        symbol=self.symbol,
                        quantity=trade_qty,
                        price=candle.close_price,
                        action="SELL",
                    )
                    self.portfolio.add_trade(trade)
                    await self.save_trade(trade)
                    logger.info(f"LIVE PAPER TRADE: SELL {trade_qty} at {candle.close_price}")
