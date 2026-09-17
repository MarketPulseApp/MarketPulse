from __future__ import annotations

import asyncio
import io

from minio import Minio

BUCKET = "models"


class ModelRepository:
    """Persist serialised ML model artefacts in MinIO."""

    def __init__(self, client: Minio) -> None:
        self.client = client
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        if not self.client.bucket_exists(BUCKET):
            self.client.make_bucket(BUCKET)

    @staticmethod
    def _key(symbol: str, model_name: str, version: str, ext: str) -> str:
        return f"models/{symbol}/{model_name}/{version}.{ext}"

    async def upload(
        self,
        symbol: str,
        model_name: str,
        version: str,
        file_bytes: bytes,
        ext: str = "pkl",
    ) -> None:
        """Upload a serialised model file."""
        key = self._key(symbol, model_name, version, ext)
        await asyncio.to_thread(
            self.client.put_object,
            BUCKET,
            key,
            io.BytesIO(file_bytes),
            length=len(file_bytes),
            content_type="application/octet-stream",
        )

    async def download(
        self,
        symbol: str,
        model_name: str,
        version: str,
        ext: str = "pkl",
    ) -> bytes:
        """Download a model and return its raw bytes."""
        key = self._key(symbol, model_name, version, ext)

        def _get() -> bytes:
            response = self.client.get_object(BUCKET, key)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()

        return await asyncio.to_thread(_get)

    async def list_versions(self, symbol: str, model_name: str) -> list[str]:
        """List all stored versions for a given symbol+model pair."""
        prefix = f"models/{symbol}/{model_name}/"

        def _list() -> list[str]:
            return [obj.object_name for obj in self.client.list_objects(BUCKET, prefix=prefix)]

        return await asyncio.to_thread(_list)

    async def delete(self, symbol: str, model_name: str, version: str, ext: str = "pkl") -> None:
        """Delete a specific model version."""
        key = self._key(symbol, model_name, version, ext)
        await asyncio.to_thread(self.client.remove_object, BUCKET, key)
