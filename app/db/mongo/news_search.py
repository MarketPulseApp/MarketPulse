from __future__ import annotations

from datetime import UTC, datetime, timedelta

from motor.motor_asyncio import AsyncIOMotorDatabase


class NewsSearchRepository:
    """Full-text search over news articles via MongoDB text index.

    Replaces Elasticsearch. MongoDB's $text operator uses a trigram/stemmed
    index over the headline and summary fields. For the query volumes a
    market-intelligence app produces this is more than adequate and removes
    the 2 GB Elasticsearch service from the stack.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.col = db["news_articles"]

    async def initialize(self) -> None:
        """Create the text index. Call once at startup."""
        await self.col.create_index(
            [("headline", "text"), ("summary", "text")],
            name="news_text_search",
            default_language="english",
            weights={"headline": 2, "summary": 1},
        )

    async def search(
        self,
        query: str,
        symbol: str | None = None,
        days: int = 7,
        size: int = 20,
    ) -> list[dict]:
        """Full-text search with optional symbol filter and date window.

        Returns dicts with keys matching the news_articles collection schema.
        Results are ordered by text-match score descending, then recency.
        """
        cutoff = datetime.now(UTC) - timedelta(days=days)

        filt: dict = {
            "$text": {"$search": query},
            "published_at": {"$gte": cutoff},
        }
        if symbol:
            filt["symbol"] = symbol

        cursor = (
            self.col.find(filt, {"score": {"$meta": "textScore"}})
            .sort([("score", {"$meta": "textScore"}), ("published_at", -1)])
            .limit(size)
        )
        docs = await cursor.to_list(length=size)
        for doc in docs:
            doc.pop("_id", None)
        return docs

    async def delete(self, url: str) -> None:
        """Remove a news article from the collection by URL."""
        await self.col.delete_one({"url": url})
