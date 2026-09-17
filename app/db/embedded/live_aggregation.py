from __future__ import annotations

import asyncio

import duckdb

# DuckDB is synchronous. Wrap all calls in asyncio.to_thread().
# An in-memory database starts empty on every restart — rebuild it
# from Parquet/MinIO/Valkey during the startup sequence.


class LiveAggregationRepository:
    """In-memory DuckDB aggregations rebuilt from upstream Parquet data.

    DuckDB can query Parquet files directly with read_parquet(), making it
    ideal for fast analytical queries without loading data into a full OLAP
    store. The in-memory database is fast but volatile — always treat it as
    a read cache, not a source of truth.
    """

    def __init__(self) -> None:
        self._conn = duckdb.connect(database=":memory:")
        self._setup()

    def _setup(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ohlcv_today (
                symbol      VARCHAR,
                open        DOUBLE,
                high        DOUBLE,
                low         DOUBLE,
                close       DOUBLE,
                volume      BIGINT,
                timestamp   TIMESTAMP
            )
        """
        )

    def _load_from_parquet(self, parquet_glob: str) -> None:
        """Replace the in-memory table from a glob of Parquet files.

        Example:  /data/parquet/ohlcv/AAPL/*.parquet
                  s3://bucket/parquet/ohlcv/*/*.parquet  (with httpfs extension)
        """
        self._conn.execute("DELETE FROM ohlcv_today")
        self._conn.execute(
            "INSERT INTO ohlcv_today SELECT * FROM read_parquet(?)",
            [parquet_glob],
        )

    def _get_daily_summary(self) -> list[dict]:
        result = self._conn.execute(
            """
            SELECT
                symbol,
                first(open  ORDER BY timestamp ASC)  AS open,
                max(high)                             AS high,
                min(low)                              AS low,
                last(close  ORDER BY timestamp ASC)  AS close,
                sum(volume)                           AS total_volume,
                count(*)                              AS bar_count
            FROM ohlcv_today
            GROUP BY symbol
            ORDER BY symbol
        """
        ).fetchdf()
        return result.to_dict("records")

    def _get_top_movers(self, n: int = 10) -> list[dict]:
        result = self._conn.execute(
            f"""
            SELECT
                symbol,
                first(open  ORDER BY timestamp ASC)  AS open,
                last(close  ORDER BY timestamp ASC)  AS close,
                (last(close ORDER BY timestamp ASC) - first(open ORDER BY timestamp ASC))
                    / first(open ORDER BY timestamp ASC) * 100  AS pct_change
            FROM ohlcv_today
            GROUP BY symbol
            ORDER BY abs(pct_change) DESC
            LIMIT {n}
        """
        ).fetchdf()
        return result.to_dict("records")

    def _query(self, sql: str, params: list | None = None) -> list[dict]:
        rel = self._conn.execute(sql, params or [])
        return rel.fetchdf().to_dict("records")

    async def refresh(self, parquet_glob: str) -> None:
        """Reload in-memory data from Parquet files matching *parquet_glob*."""
        await asyncio.to_thread(self._load_from_parquet, parquet_glob)

    async def get_daily_summary(self) -> list[dict]:
        return await asyncio.to_thread(self._get_daily_summary)

    async def get_top_movers(self, n: int = 10) -> list[dict]:
        return await asyncio.to_thread(self._get_top_movers, n)

    async def query(self, sql: str, params: list | None = None) -> list[dict]:
        """Run arbitrary SQL against the in-memory dataset."""
        return await asyncio.to_thread(self._query, sql, params)
