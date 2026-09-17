from __future__ import annotations

from datetime import UTC, datetime, timedelta

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

# NewsArticle must exist at app.domain.news — create it if it does not yet exist:
#
# @dataclass
# class NewsArticle:
#     url: str
#     headline: str
#     symbol: str
#     source: str
#     published_at: datetime
#     summary: str = ""
#     vader_score: float | None = None
#     finbert_score: float | None = None
from app.domain.news import NewsArticle  # type: ignore[import]


class NewsArticleRepository:
    """Persist and query news articles in MongoDB."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.col = db["news_articles"]

    async def initialize(self) -> None:
        """Create indexes. Call once at startup."""
        await self.col.create_index("url", unique=True)
        await self.col.create_index([("symbol", 1), ("published_at", -1)])
        await self.col.create_index("finbert_score")

    async def insert(self, article: NewsArticle) -> bool:
        """Insert an article. Returns False if the URL already exists."""
        doc = article.to_mongo_doc()
        try:
            await self.col.insert_one(doc)
            return True
        except DuplicateKeyError:
            return False

    async def get_recent(self, symbol: str, hours: int = 24) -> list[NewsArticle]:
        """Return articles for *symbol* published within the last *hours*."""
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        cursor = (
            self.col.find({"symbol": symbol, "published_at": {"$gte": cutoff}})
            .sort("published_at", -1)
            .limit(100)
        )
        rows = await cursor.to_list(length=100)
        return [self._to_domain(doc) for doc in rows]

    async def get_unscored(self, limit: int = 50) -> list[NewsArticle]:
        """Return articles that have not yet been run through FinBERT."""
        cursor = self.col.find({"finbert_score": None}).limit(limit)
        rows = await cursor.to_list(length=limit)
        return [self._to_domain(doc) for doc in rows]

    async def update_score(
        self,
        url: str,
        vader_score: float,
        finbert_score: float,
    ) -> None:
        """Write sentiment scores back to an existing article."""
        await self.col.update_one(
            {"url": url},
            {"$set": {"vader_score": vader_score, "finbert_score": finbert_score}},
        )

    @staticmethod
    def _to_domain(doc: dict) -> NewsArticle:
        doc.pop("_id", None)
        return NewsArticle(**doc)
