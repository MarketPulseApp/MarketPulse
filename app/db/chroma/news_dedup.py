from __future__ import annotations

from typing import Any


class NewsDeduplicationRepository:
    """Semantic deduplication for news articles using vector embeddings."""

    def __init__(self, client: Any) -> None:
        self.client = client
        self._collection = None

    async def _get_collection(self):
        if self._collection is None:
            self._collection = await self.client.get_or_create_collection(
                name="news_dedup",
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    async def is_duplicate(self, embedding: list[float], threshold: float = 0.95) -> bool:
        """
        Return True if a semantically similar article already exists.

        ChromaDB returns cosine *distance* (0 = identical, 2 = opposite).
        Similarity = 1 - distance, so threshold=0.95 means the program accepts anything
        with distance <= 0.05 as a duplicate
        """
        collection = await self._get_collection()
        if await collection.count() == 0:
            return False

        result = await collection.query(
            query_embeddings=[embedding],
            n_results=1,
            include=["distances"],
        )
        distance: float = result["distances"][0][0]
        return distance <= (1.0 - threshold)

    async def add(
        self,
        article_id: str,
        embedding: list[float],
        metadata: dict,
    ) -> None:
        """Store an article embedding. Use the article URL as *article_id*."""
        collection = await self._get_collection()
        await collection.add(
            ids=[article_id],
            embeddings=[embedding],
            metadatas=[metadata],
        )
