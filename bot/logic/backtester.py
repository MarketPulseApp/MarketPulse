"""
Logic layer for executing backtests.
"""

import logging
from datetime import datetime

from data_access.loader import MarketDataLoader
from domain.models import Portfolio, Trade
from logic.risk_manager import RiskManager
from logic.strategy import MLStrategy

logger = logging.getLogger(__name__)


class Backtester:
    """Orchestrates the backtesting simulation."""

    def __init__(
        self,
        data_loader: MarketDataLoader,
        strategy: MLStrategy,
        risk_manager: RiskManager | None = None,
        initial_capital: float = 10000.0,
    ):
        """
        Initialize the backtester.

        Args:
            data_loader (MarketDataLoader): Loads historical data.
            strategy (MLStrategy): Determines trade actions.
            risk_manager (RiskManager, optional): Risk management module.
            initial_capital (float): Starting portfolio cash.
        """
        self.data_loader = data_loader
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.portfolio = Portfolio(initial_capital)

    async def run(self, symbol: str, start_time: datetime, periods: int) -> dict:
        """
        Execute the backtest.

        Args:
            symbol (str): Asset to trade.
            start_time (datetime): Start time of backtest.
            periods (int): Number of time periods to run.

        Returns:
            dict: Summary metrics of the backtest performance.
        """
        logger.info(f"Starting backtest for {symbol}, {periods} periods.")

        # Load data
        historical_data = self.data_loader.load_historical_data(symbol, start_time, periods)

        # Simulate over time
        for i, candle in enumerate(historical_data):
            current_prices = {symbol: candle.close_price}

            # 1. Update Risk Manager State
            if self.risk_manager:
                portfolio_value = self.portfolio.get_total_value(current_prices)
                self.risk_manager.update_state(candle.timestamp, portfolio_value)

                if self.risk_manager.is_halted:
                    logger.warning(
                        f"Backtest halted at {candle.timestamp}: {self.risk_manager.halt_reason}"
                    )
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
                            logger.info(f"LIQUIDATED {sym} position due to Risk Halt.")
                    break

            # 2. Get Trading Signal
            signal = await self.strategy.get_signal(candle)

            # 3. Vet Order through Risk Manager (if present)
            trade_qty = 1.0

            if signal == "BUY":
                if self.risk_manager:
                    allowed, qty = self.risk_manager.vet_order(
                        "BUY", candle.close_price, self.portfolio, current_prices
                    )
                    if not allowed:
                        continue
                    trade_qty = qty

                cost = trade_qty * candle.close_price
                if self.portfolio.cash >= cost:
                    # Execute Primary Trade
                    trade = Trade(
                        timestamp=candle.timestamp,
                        symbol=symbol,
                        quantity=trade_qty,
                        price=candle.close_price,
                        action="BUY",
                    )
                    self.portfolio.add_trade(trade)
                    logger.debug(f"Executed BUY at {candle.close_price} qty {trade_qty}")

                    # Execute Delta-Neutral Hedge (Short Market Index)
                    hedge_symbol = f"HEDGE_{symbol}"
                    hedge_trade = Trade(
                        timestamp=candle.timestamp,
                        symbol=hedge_symbol,
                        quantity=trade_qty,
                        price=candle.close_price,  # Simplified mock hedge
                        action="SELL",  # Shorting to remain delta neutral
                    )
                    self.portfolio.add_trade(hedge_trade)
                    logger.debug(f"Executed Delta-Neutral HEDGE (SELL) on {hedge_symbol}")

            elif signal == "SELL":
                pos = self.portfolio.positions.get(symbol)
                if pos and pos.quantity > 0:
                    if self.risk_manager:
                        allowed, _ = self.risk_manager.vet_order(
                            "SELL", candle.close_price, self.portfolio, current_prices
                        )
                        if not allowed:
                            continue
                        trade_qty = pos.quantity  # Sell entire position by default
                    else:
                        trade_qty = min(1.0, pos.quantity)

                    # Execute Primary Sell
                    trade = Trade(
                        timestamp=candle.timestamp,
                        symbol=symbol,
                        quantity=trade_qty,
                        price=candle.close_price,
                        action="SELL",
                    )
                    self.portfolio.add_trade(trade)
                    logger.debug(f"Executed SELL at {candle.close_price} qty {trade_qty}")

                    # Unwind Delta-Neutral Hedge
                    hedge_symbol = f"HEDGE_{symbol}"
                    hedge_trade = Trade(
                        timestamp=candle.timestamp,
                        symbol=hedge_symbol,
                        quantity=trade_qty,
                        price=candle.close_price,
                        action="BUY",  # Buy to cover short
                    )
                    self.portfolio.add_trade(hedge_trade)
                    logger.debug(f"Unwound Delta-Neutral HEDGE (BUY) on {hedge_symbol}")

        final_price = historical_data[-1].close_price if historical_data else 0.0
        current_prices = {symbol: final_price}
        final_value = self.portfolio.get_total_value(current_prices)

        metrics = {
            "initial_value": self.portfolio.initial_cash,
            "final_value": final_value,
            "net_profit": final_value - self.portfolio.initial_cash,
            "return_pct": ((final_value / self.portfolio.initial_cash) - 1.0) * 100.0,
            "total_trades": len(self.portfolio.trade_history),
            "halted": self.risk_manager.is_halted if self.risk_manager else False,
            "halt_reason": self.risk_manager.halt_reason if self.risk_manager else None,
        }

        logger.info(f"Backtest complete. Metrics: {metrics}")
        return metrics
