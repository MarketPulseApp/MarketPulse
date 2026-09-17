"""
Logic layer module for Risk Management.
"""

import logging
from datetime import date, datetime

from domain.models import Portfolio

logger = logging.getLogger(__name__)


class RiskManager:
    """
    Manages trading risks including position sizing, drawdown limits, and daily loss thresholds.
    """

    def __init__(
        self,
        max_drawdown_pct: float = 0.05,
        max_daily_loss_pct: float = 0.02,
        risk_per_trade_pct: float = 0.01,
    ):
        """
        Initialize the Risk Manager.

        Args:
            max_drawdown_pct (float): Maximum allowed drawdown from peak portfolio value before halting (e.g., 0.05 for 5%).
            max_daily_loss_pct (float): Maximum allowed loss in a single trading day before halting (e.g., 0.02 for 2%).
            risk_per_trade_pct (float): Percentage of current equity to risk on a single trade (e.g., 0.01 for 1%).
        """
        self.max_drawdown_pct = max_drawdown_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.risk_per_trade_pct = risk_per_trade_pct

        self.peak_value: float = 0.0
        self.is_halted: bool = False
        self.halt_reason: str = ""

        self.current_day: date | None = None
        self.start_of_day_value: float = 0.0

    def update_state(self, current_time: datetime, portfolio_value: float):
        """
        Update the internal risk state with the current portfolio value.
        Checks for drawdown or daily loss breaches.

        Args:
            current_time (datetime): Current market time.
            portfolio_value (float): Total current value of the portfolio.
        """
        if self.is_halted:
            return

        # Initialize peak
        if self.peak_value == 0.0:
            self.peak_value = portfolio_value

        # Update peak
        if portfolio_value > self.peak_value:
            self.peak_value = portfolio_value

        # Initialize/Update daily tracking
        if self.current_day != current_time.date():
            self.current_day = current_time.date()
            self.start_of_day_value = portfolio_value

        # Check Drawdown
        drawdown = (self.peak_value - portfolio_value) / self.peak_value
        if drawdown >= self.max_drawdown_pct:
            self.is_halted = True
            self.halt_reason = f"Max Drawdown Limit Reached: {drawdown*100:.2f}% >= {self.max_drawdown_pct*100:.2f}%"
            logger.warning(f"TRADING HALTED: {self.halt_reason}")
            return

        # Check Daily Loss
        daily_loss = (self.start_of_day_value - portfolio_value) / self.start_of_day_value
        if daily_loss >= self.max_daily_loss_pct:
            self.is_halted = True
            self.halt_reason = f"Max Daily Loss Limit Reached: {daily_loss*100:.2f}% >= {self.max_daily_loss_pct*100:.2f}%"
            logger.warning(f"TRADING HALTED: {self.halt_reason}")
            return

    def vet_order(
        self, action: str, price: float, portfolio: Portfolio, current_prices: dict[str, float]
    ) -> tuple[bool, float]:
        """
        Vet an order and determine position sizing based on risk parameters.

        Args:
            action (str): 'BUY' or 'SELL'.
            price (float): The current price of the asset.
            portfolio (Portfolio): Current portfolio state.
            current_prices (Dict[str, float]): Map of all current asset prices.

        Returns:
            Tuple[bool, float]: A boolean indicating if the trade is allowed, and the allowed quantity (0.0 if not allowed).
        """
        if self.is_halted:
            return False, 0.0

        portfolio_value = portfolio.get_total_value(current_prices)

        if action == "BUY":
            # Dynamic position sizing: Risk a fixed percentage of equity
            risk_amount = portfolio_value * self.risk_per_trade_pct

            # Simplified sizing: assuming we might lose 100% of the position if things go extremely bad,
            # or in a real scenario we'd use stop-loss distance.
            # For this exercise, let's size the position such that the total capital allocated to the trade
            # is limited by risk_amount (a bit conservative) or assume a 10% stop loss.
            # Let's assume a 10% stop loss for sizing:
            assumed_stop_loss_pct = 0.10
            capital_to_allocate = risk_amount / assumed_stop_loss_pct

            quantity = capital_to_allocate / price

            # Ensure we don't exceed available cash
            max_qty_by_cash = portfolio.cash / price
            quantity = min(quantity, max_qty_by_cash)

            if quantity >= 0.01:
                return True, round(quantity, 4)
            return False, 0.0

        elif action == "SELL":
            # For sells, we just approve selling the full existing position if any.
            # Sizing logic would typically just pass the quantity to sell, but here we'll
            # assume the caller will figure out the exact quantity or we return a generic multiplier.
            # Returning True and 1.0 (to signify 100% of position) or similar.
            # Let's just return True, 0.0, and let the caller use the position quantity.
            return True, 0.0

        return False, 0.0
