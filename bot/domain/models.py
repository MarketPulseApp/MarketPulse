"""
Data Domain models for the backtesting engine.
Contains structural representations of market data, orders, and portfolio state.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class MarketData:
    """Represents a single slice of market data (e.g., a candle)."""

    timestamp: datetime
    symbol: str
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float


@dataclass
class Position:
    """Represents a current trading position."""

    symbol: str
    quantity: float
    average_price: float


@dataclass
class Trade:
    """Represents a completed trade."""

    timestamp: datetime
    symbol: str
    quantity: float
    price: float
    action: str  # 'BUY' or 'SELL'


class Portfolio:
    """Tracks the current balances and positions."""

    def __init__(self, initial_cash: float):
        """
        Initialize portfolio with initial cash.

        Args:
            initial_cash (float): Starting cash amount.
        """
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions: dict[str, Position] = {}
        self.trade_history: list[Trade] = []

    def update_cash(self, amount: float):
        """
        Update cash balance.

        Args:
            amount (float): Amount to add (can be negative).
        """
        self.cash += amount

    def add_trade(self, trade: Trade):
        """
        Record a trade and update positions/cash.

        Args:
            trade (Trade): The executed trade.
        """
        self.trade_history.append(trade)

        pos = self.positions.get(trade.symbol, Position(trade.symbol, 0.0, 0.0))

        if trade.action == "BUY":
            cost = trade.quantity * trade.price
            self.cash -= cost

            total_qty = pos.quantity + trade.quantity
            if total_qty > 0:
                pos.average_price = ((pos.quantity * pos.average_price) + cost) / total_qty
            pos.quantity = total_qty

        elif trade.action == "SELL":
            revenue = trade.quantity * trade.price
            self.cash += revenue

            pos.quantity -= trade.quantity
            if pos.quantity == 0:
                pos.average_price = 0.0

        self.positions[trade.symbol] = pos

    def get_total_value(self, current_prices: dict[str, float]) -> float:
        """
        Calculate total portfolio value (cash + open positions).

        Args:
            current_prices (Dict[str, float]): Map of symbol to its current market price.

        Returns:
            float: Total portfolio value.
        """
        value = self.cash
        for symbol, pos in self.positions.items():
            if symbol in current_prices:
                value += pos.quantity * current_prices[symbol]
        return value
