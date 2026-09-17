from __future__ import annotations

from typing import Any


class RedditClusterRepository:
    """Cluster Reddit posts by semantic similarity."""

    def __init__(self, client: Any) -> None:
        self.client = client
        self._collection = None

    async def _get_collection(self):
        if self._collection is None:
            self._collection = await self.client.get_or_create_collection(
                name="reddit_posts", metadata={"hnsw:space", "cosine"}
            )
        return self._collection

    async def add(self, post_id: str, embedding: list[float]) -> None:
        """Index a post embedding"""
        collection = await self._get_collection()
        await collection.add(ids=[post_id], embedding=[embedding])

    async def find_similar(self, embedding: list[float], n: int = 5) -> list[str]:
        """Return the n post_ids most semantically similar to *embedding*."""
        collection = await self._get_collection()
        count = await collection.count()
        if count == 0:
            return []

        n = min(n, count)
        result = await collection.query(
            query_embeddings=[embedding], n_results=n, include=["distances"]
        )
        return result["ids"][0]

    async def delete(self, post_id: str) -> None:
        """Remove a post from the index."""
        collection = await self._get_collection()
        await collection.delete(ids=[post_id])
