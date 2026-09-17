from __future__ import annotations

import asyncio
import io
from datetime import UTC, datetime, timedelta

from minio import Minio

BUCKET = "reports"
CONTENT_TYPES = {
    "pdf": "application/pdf",
    "csv": "text/csv",
    "json": "application/json",
    "xml": "application/xml",
    "html": "text/html",
}


class ReportRepository:
    """Store generated reports (PDF, CSV, JSON, XML, HTML) in MinIO."""

    def __init__(self, client: Minio) -> None:
        self.client = client
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        if not self.client.bucket_exists(BUCKET):
            self.client.make_bucket(BUCKET)

    @staticmethod
    def _key(symbol: str, fmt: str) -> str:
        ts = datetime.now(UTC).isoformat(timespec="seconds")
        return f"reports/{symbol}/{ts}.{fmt}"

    async def upload(self, symbol: str, fmt: str, file_bytes: bytes) -> str:
        """Upload a report and return a 24-hour presigned download URL."""
        key = self._key(symbol, fmt)
        content_type = CONTENT_TYPES.get(fmt.lower(), "application/octet-stream")
        data = io.BytesIO(file_bytes)

        await asyncio.to_thread(
            self.client.put_object,
            BUCKET,
            key,
            data,
            length=len(file_bytes),
            content_type=content_type,
        )

        url = await asyncio.to_thread(
            self.client.presigned_get_object,
            BUCKET,
            key,
            expires=timedelta(hours=24),
        )
        return url

    async def list_keys(self, symbol: str) -> list[str]:
        prefix = f"reports/{symbol}/"

        def _list():
            return [obj.object_name for obj in self.client.list_objects(BUCKET, prefix=prefix)]

        return await asyncio.to_thread(_list)
