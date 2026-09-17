from __future__ import annotations

import dataclasses

from motor.motor_asyncio import AsyncIOMotorDatabase

# PredictionExplanation must exist at app.domain.explanation:
#
# @dataclass
# class PredictionExplanation:
#     prediction_id: str
#     symbol: str
#     horizon: str
#     features: dict          # SHAP values or feature importances
#     explanation: str        # Human-readable LLM summary
#     created_at: datetime
from app.domain.explanation import PredictionExplanation  # type: ignore[import]


class PredictionExplanationRepository:
    """Persist SHAP feature explanations for model predictions in MongoDB."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.col = db["prediction_explanations"]

    async def initialize(self) -> None:
        await self.col.create_index("prediction_id", unique=True)
        await self.col.create_index([("symbol", 1), ("created_at", -1)])

    async def insert(self, explanation: PredictionExplanation) -> None:
        doc = dataclasses.asdict(explanation)
        await self.col.insert_one(doc)

    async def get_for_prediction(self, prediction_id: str) -> PredictionExplanation | None:
        doc = await self.col.find_one({"prediction_id": prediction_id})
        if doc is None:
            return None
        return self._to_domain(doc)

    async def get_recent(self, symbol: str, limit: int = 10) -> list[PredictionExplanation]:
        cursor = self.col.find({"symbol": symbol}).sort("created_at", -1).limit(limit)
        rows = await cursor.to_list(length=limit)
        return [self._to_domain(doc) for doc in rows]

    @staticmethod
    def _to_domain(doc: dict) -> PredictionExplanation:
        doc.pop("_id", None)
        return PredictionExplanation(**doc)
