from __future__ import annotations

from datetime import UTC, datetime, timedelta

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

# RedditPost must exist at app.domain.reddit:
#
# @dataclass
# class RedditPost:
#     post_id: str
#     subreddit: str
#     title: str
#     body: str
#     symbol: str
#     score: int
#     created_at: datetime
#     sentiment_score: float | None = None
from app.domain.reddit import RedditPost  # type: ignore[import]


class RedditPostRepository:
    """Persist and query Reddit posts in MongoDB."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.col = db["reddit_posts"]

    async def initialize(self) -> None:
        await self.col.create_index("post_id", unique=True)
        await self.col.create_index([("symbol", 1), ("created_at", -1)])
        await self.col.create_index("subreddit")

    async def insert(self, post: RedditPost) -> bool:
        """Insert a post. Returns False if post_id already exists."""
        doc = post.to_mongo_doc()
        try:
            await self.col.insert_one(doc)
            return True
        except DuplicateKeyError:
            return False

    async def get_recent(
        self,
        symbol: str,
        hours: int = 24,
        subreddit: str | None = None,
    ) -> list[RedditPost]:
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        filt: dict = {"symbol": symbol, "created_at": {"$gte": cutoff}}
        if subreddit:
            filt["subreddit"] = subreddit
        cursor = self.col.find(filt).sort("created_at", -1).limit(200)
        rows = await cursor.to_list(length=200)
        return [self._to_domain(doc) for doc in rows]

    async def get_unscored(self, limit: int = 50) -> list[RedditPost]:
        cursor = self.col.find({"sentiment_score": None}).limit(limit)
        rows = await cursor.to_list(length=limit)
        return [self._to_domain(doc) for doc in rows]

    async def update_sentiment(self, post_id: str, sentiment_score: float) -> None:
        await self.col.update_one(
            {"post_id": post_id},
            {"$set": {"sentiment_score": sentiment_score}},
        )

    @staticmethod
    def _to_domain(doc: dict) -> RedditPost:
        doc.pop("_id", None)
        return RedditPost(**doc)
