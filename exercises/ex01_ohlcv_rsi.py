# exercises/ex01_ohlcv_rsi.py
"""
Fetch AAPL OHLCV data and compute RSI-14 from scratch.
Verifies understanding of: yfinance, OHLCV structure, RSI formula.
"""

import yfinance as yf
import pandas as pd
import numpy as np

# ── Step 1: Fetch OHLCV ──────────────────────────────────────────────────────
ticker = yf.Ticker("AAPL")
df = ticker.history(period="2y")  # 2 years of daily data
df.index = pd.to_datetime(df.index)
df.index = df.index.tz_localize(None)  # Remove timezone for simplicity
print(f"Fetched {len(df)} rows of AAPL OHLCV data")
print(df[["Open", "High", "Low", "Close", "Volume"]].tail(3).to_string())
print()

# ── Step 2: RSI from scratch ──────────────────────────────────────────────────
def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """
    RSI formula:
    1. Compute daily price change: delta = close - close.shift(1)
    2. Separate into gains (delta where delta > 0, else 0) and losses (abs(delta where delta < 0))
    3. Compute exponential moving average of gains and losses over `period` days
    4. RS = avg_gain / avg_loss
    5. RSI = 100 - (100 / (1 + RS))
    """
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    # Wilder's smoothing (equivalent to EMA with alpha=1/period)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

rsi_scratch = compute_rsi(df["Close"], period=14)

# ── Step 3: Verify against ta ─────────────────────────────────────────────────
from ta.momentum import RSIIndicator
rsi_ta = RSIIndicator(close=df["Close"], window=14).rsi()

# Compare last 5 rows (first 14 rows are NaN due to warmup)
comparison = pd.DataFrame({
    "scratch": rsi_scratch,
    "ta":      rsi_ta,
    "diff":    (rsi_scratch - rsi_ta).abs()
}).dropna().tail(5)

print("RSI comparison (last 5 trading days):")
print(comparison.round(4).to_string())

max_diff = comparison["diff"].max()
assert max_diff < 0.01, f"RSI mismatch! Max difference: {max_diff:.4f}"
print(f"\n✓ RSI from scratch matches ta (max diff: {max_diff:.6f})")

# ── Step 4: Summary ──────────────────────────────────────────────────────────
latest_rsi = rsi_scratch.iloc[-1]
latest_close = df["Close"].iloc[-1]
print(f"\nAAPL summary:")
print(f"  Latest close: ${latest_close:.2f}")
print(f"  RSI-14:       {latest_rsi:.1f}")
if latest_rsi > 70:
    print("  Signal:       OVERBOUGHT (>70)")
elif latest_rsi < 30:
    print("  Signal:       OVERSOLD (<30)")
else:
    print("  Signal:       NEUTRAL")