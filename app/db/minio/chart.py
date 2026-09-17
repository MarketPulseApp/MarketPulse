from __future__ import annotations

import asyncio
import io
from datetime import UTC, datetime, timedelta

from minio import Minio

BUCKET = "charts"


class ChartRepository:
    """Store and retrieve chart PNG images in MinIO."""

    def __init__(self, client: Minio) -> None:
        self.client = client
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        if not self.client.bucket_exists(BUCKET):
            self.client.make_bucket(BUCKET)

    @staticmethod
    def _key(symbol: str) -> str:
        ts = datetime.now(UTC).isoformat(timespec="seconds")
        return f"charts/{symbol}/{ts}.png"

    async def upload(self, symbol: str, chart_bytes: bytes) -> str:
        """Upload chart bytes and return a 1-hour presigned URL."""
        key = self._key(symbol)
        data = io.BytesIO(chart_bytes)

        await asyncio.to_thread(
            self.client.put_object,
            BUCKET,
            key,
            data,
            length=len(chart_bytes),
            content_type="image/png",
        )

        url = await asyncio.to_thread(
            self.client.presigned_get_object,
            BUCKET,
            key,
            expires=timedelta(hours=1),
        )
        return url

    async def get_url(self, key: str, ttl_hours: int = 1) -> str:
        """Generate a fresh presigned GET URL for an existing object key."""
        return await asyncio.to_thread(
            self.client.presigned_get_object,
            BUCKET,
            key,
            expires=timedelta(hours=ttl_hours),
        )

    async def list_keys(self, symbol: str) -> list[str]:
        """List all chart object keys for *symbol*."""
        prefix = f"charts/{symbol}/"

        def _list():
            return [obj.object_name for obj in self.client.list_objects(BUCKET, prefix=prefix)]

        return await asyncio.to_thread(_list)
