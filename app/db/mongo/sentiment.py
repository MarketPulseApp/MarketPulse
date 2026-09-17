from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient


class SentimentRepository:
    def __init__(self, client: AsyncIOMotorClient):
        self.client = client
        self.db = self.client.get_database("marketpulse")
        self.news_collection = self.db.get_collection("news")
        self.reddit_collection = self.db.get_collection("reddit")

    async def insert_news(self, records: list[dict[str, Any]]) -> None:
        if records:
            await self.news_collection.insert_many(records)

    async def insert_reddit(self, records: list[dict[str, Any]]) -> None:
        if records:
            await self.reddit_collection.insert_many(records)
