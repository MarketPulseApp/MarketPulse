from __future__ import annotations

import asyncio

import duckdb

# Persistent DuckDB — survives restarts. Used for prediction accuracy tracking.
# DuckDB is sync; wrap calls in asyncio.to_thread().

CREATE_PREDICTIONS = """
CREATE TABLE IF NOT EXISTS resolved_predictions (
    id          VARCHAR PRIMARY KEY,
    symbol      VARCHAR NOT NULL,
    horizon     VARCHAR NOT NULL,
    direction   VARCHAR NOT NULL,
    confidence  DOUBLE  NOT NULL,
    was_correct BOOLEAN NOT NULL,
    resolved_at TIMESTAMP NOT NULL,
    predicted_at TIMESTAMP NOT NULL
)
"""
CREATE_IDX = """
CREATE INDEX IF NOT EXISTS idx_rp_symbol_horizon
    ON resolved_predictions (symbol, horizon, resolved_at DESC)
"""


class AccuracyAnalyticsRepository:
    """Persistent DuckDB store for resolved prediction accuracy analytics.

    After a prediction's horizon elapses we mark it correct or incorrect.
    This table accumulates those resolved rows so we can compute rolling
    accuracy, calibration curves, and model drift metrics.
    """

    def __init__(self, db_path: str) -> None:
        self._conn = duckdb.connect(database=db_path)
        self._conn.execute(CREATE_PREDICTIONS)
        self._conn.execute(CREATE_IDX)

    def _insert(self, row: dict) -> None:
        self._conn.execute(
            """
            INSERT OR IGNORE INTO resolved_predictions
                (id, symbol, horizon, direction, confidence, was_correct, resolved_at, predicted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                row["id"],
                row["symbol"],
                row["horizon"],
                row["direction"],
                row["confidence"],
                row["was_correct"],
                row["resolved_at"],
                row["predicted_at"],
            ],
        )

    def _rolling_accuracy(self, symbol: str, horizon: str, window: int) -> float:
        result = self._conn.execute(
            """
            SELECT avg(CASE WHEN was_correct THEN 1.0 ELSE 0.0 END) AS accuracy
            FROM (
                SELECT was_correct
                FROM resolved_predictions
                WHERE symbol = ? AND horizon = ?
                ORDER BY resolved_at DESC
                LIMIT ?
            )
            """,
            [symbol, horizon, window],
        ).fetchone()
        return float(result[0]) if result and result[0] is not None else 0.0

    def _calibration(self, symbol: str, horizon: str, buckets: int = 10) -> list[dict]:
        """Bin predictions by confidence decile and compute accuracy per bin."""
        result = self._conn.execute(
            f"""
            SELECT
                floor(confidence * {buckets}) / {buckets}    AS conf_bin,
                count(*)                                       AS n,
                avg(CASE WHEN was_correct THEN 1.0 ELSE 0.0 END) AS accuracy
            FROM resolved_predictions
            WHERE symbol = ? AND horizon = ?
            GROUP BY conf_bin
            ORDER BY conf_bin
            """,
            [symbol, horizon],
        ).fetchdf()
        return result.to_dict("records")

    def _overall_accuracy(self, symbol: str, horizon: str) -> dict:
        result = self._conn.execute(
            """
            SELECT
                count(*)                                         AS total,
                sum(CASE WHEN was_correct THEN 1 ELSE 0 END)      AS correct,
                avg(CASE WHEN was_correct THEN 1.0 ELSE 0.0 END)  AS accuracy
            FROM resolved_predictions
            WHERE symbol = ? AND horizon = ?
            """,
            [symbol, horizon],
        ).fetchone()

        # Guard against NoneType return before subscripting
        if not result:
            return {"total": 0, "correct": 0, "accuracy": 0.0}

        return {
            "total": result[0] or 0,
            "correct": result[1] or 0,
            "accuracy": float(result[2]) if result[2] is not None else 0.0,
        }

    async def insert_resolved(self, row: dict) -> None:
        """Record a resolved prediction. *row* must have all required keys."""
        await asyncio.to_thread(self._insert, row)

    async def get_rolling_accuracy(
        self,
        symbol: str,
        horizon: str,
        window: int = 100,
    ) -> float:
        """Return accuracy over the last *window* resolved predictions."""
        return await asyncio.to_thread(self._rolling_accuracy, symbol, horizon, window)

    async def get_calibration(
        self,
        symbol: str,
        horizon: str,
        buckets: int = 10,
    ) -> list[dict]:
        """Return per-confidence-bucket accuracy for calibration analysis."""
        return await asyncio.to_thread(self._calibration, symbol, horizon, buckets)

    async def get_overall_accuracy(self, symbol: str, horizon: str) -> dict:
        return await asyncio.to_thread(self._overall_accuracy, symbol, horizon)
