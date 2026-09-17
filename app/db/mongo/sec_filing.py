from __future__ import annotations

import dataclasses
from datetime import datetime, timedelta

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

# SECFiling must exist at app.domain.sec:
#
# @dataclass
# class SECFiling:
#     filing_id: str
#     ticker: str
#     form_type: str
#     filed_at: datetime
#     content: str
#     summary: str | None = None
from app.domain.sec import SECFiling  # type: ignore[import]


class SECFilingRepository:
    """Persist and query SEC filings in MongoDB."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.col = db["sec_filings"]

    async def initialize(self) -> None:
        await self.col.create_index("filing_id", unique=True)
        await self.col.create_index([("ticker", 1), ("filed_at", -1)])
        await self.col.create_index("form_type")

    async def insert(self, filing: SECFiling) -> bool:
        """Insert a filing. Returns False if filing_id already exists."""
        doc = dataclasses.asdict(filing)
        try:
            await self.col.insert_one(doc)
            return True
        except DuplicateKeyError:
            return False

    async def get_recent(
        self,
        ticker: str,
        days: int = 90,
        form_type: str | None = None,
    ) -> list[SECFiling]:
        cutoff = datetime.utcnow() - timedelta(days=days)
        filt: dict = {"ticker": ticker, "filed_at": {"$gte": cutoff}}
        if form_type:
            filt["form_type"] = form_type
        cursor = self.col.find(filt).sort("filed_at", -1).limit(50)
        rows = await cursor.to_list(length=50)
        return [self._to_domain(doc) for doc in rows]

    async def get_unsummarised(self, limit: int = 20) -> list[SECFiling]:
        cursor = self.col.find({"summary": {"$in": [None, ""]}}).limit(limit)
        rows = await cursor.to_list(length=limit)
        return [self._to_domain(doc) for doc in rows]

    async def update_summary(self, filing_id: str, summary: str) -> None:
        await self.col.update_one(
            {"filing_id": filing_id},
            {"$set": {"summary": summary}},
        )

    @staticmethod
    def _to_domain(doc: dict) -> SECFiling:
        doc.pop("_id", None)
        return SECFiling(**doc)
