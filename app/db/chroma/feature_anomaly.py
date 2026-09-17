from __future__ import annotations

from typing import Any


class FeatureAnomalyRepository:
    """Detect anomalous feature vectors against a stored baseline."""

    _BASELINE_TAG = "baseline"

    def __init__(self, client: Any) -> None:
        self.client = client
        self._collection = None

    async def _get_collection(self):
        if self._collection is None:
            self._collection = await self.client.get_or_create_collection(
                name="feature_baseline", metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    async def fit(self, vectors: list[list[float]]) -> None:
        """Replace the stored baseline with a new set of normal feature vectors."""
        collection = await self._get_collection()
        try:
            await collection.delete(where={"source": self._BASELINE_TAG})
        except Exception:
            pass  # collection may be empty; that is fine

        ids = [str(i) for i in range(len(vectors))]
        metadatas = [{"source": self._BASELINE_TAG}] * len(vectors)
        await collection.add(ids=ids, embeddings=vectors, metadatas=metadatas)

    async def score(self, vector: list[float]) -> float:
        """Return cosine distance from the nearest baseline vector.

        0.0 = perfectly normal, closer to 1.0 = anomalous.
        Returns 0.0 if no baseline has been fitted
        """
        collection = await self._get_collection()
        if await collection.count() == 0:
            return 0.0

        result = await collection.query(
            query_embeddings=[vector],
            n_results=1,
            include=["distances"],
        )
        return result["distances"][0][0]
