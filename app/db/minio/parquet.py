from __future__ import annotations

import asyncio
import io
from collections.abc import Iterator
from datetime import date, timedelta

import pandas as pd
from minio import Minio
from minio.error import S3Error

BUCKET = "parquet"


class ParquetRepository:
    """Read and write daily OHLCV data as Parquet objects in MinIO."""

    def __init__(self, client: Minio) -> None:
        self.client = client
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        if not self.client.bucket_exists(BUCKET):
            self.client.make_bucket(BUCKET)

    @staticmethod
    def _key(symbol: str, d: date) -> str:
        return f"parquet/ohlcv/{symbol}/{d.isoformat()}.parquet"

    async def write_ohlcv(self, symbol: str, d: date, df: pd.DataFrame) -> None:
        """Serialise *df* to Parquet and write it to MinIO."""
        buf = io.BytesIO()
        df.to_parquet(buf, index=False)
        data = buf.getvalue()
        await asyncio.to_thread(
            self.client.put_object,
            BUCKET,
            self._key(symbol, d),
            io.BytesIO(data),
            length=len(data),
            content_type="application/octet-stream",
        )

    async def read_ohlcv(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """Read and concatenate daily Parquet files for *symbol* over a date range.

        Missing dates (e.g. weekends, holidays) are silently skipped.
        """
        frames: list[pd.DataFrame] = []

        def _date_range() -> Iterator[date]:
            current = start_date
            while current <= end_date:
                yield current
                current += timedelta(days=1)

        for d in _date_range():
            key = self._key(symbol, d)

            def _get(k: str = key) -> bytes | None:
                try:
                    resp = self.client.get_object(BUCKET, k)
                    try:
                        return resp.read()
                    finally:
                        resp.close()
                        resp.release_conn()
                except S3Error as exc:
                    if exc.code == "NoSuchKey":
                        return None
                    raise

            raw = await asyncio.to_thread(_get)
            if raw is not None:
                frames.append(pd.read_parquet(io.BytesIO(raw)))

        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
