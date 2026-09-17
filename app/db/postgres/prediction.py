import asyncpg

from app.core.config import settings
from app.domain.prediction import Prediction


# TODO: Remove in Phase 5
async def create_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=settings.POSTGRES_DATABASE,
    )


class PredictionRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def insert(self, prediction: Prediction) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "SELECT fn_insert_prediction($1, $2, $3, $4, $5, $6, $7, $8, "
                "$9, $10, $11, $12, $13, $14, $15, $16)",
                prediction.prediction_time,
                prediction.symbol,
                prediction.horizon,
                prediction.direction,
                prediction.confidence,
                None,  # lstm_prob_up
                None,  # lstm_prob_down
                None,  # lstm_prob_flat
                None,  # xgb_prob_up
                None,  # xgb_prob_down
                None,  # xgb_prob_flat
                None,  # lgbm_prob_up
                None,  # lgbm_prob_down
                None,  # lgbm_prob_flat
                "v0",  # model_version
                1,  # feature_schema_version
            )

    async def get_latest(self, symbol: str, horizon: str) -> Prediction | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM fn_get_latest_prediction($1, $2)", symbol, horizon
            )
            if row is None:
                return None
            return Prediction(
                symbol=row["symbol"],
                horizon=row["horizon"],
                direction=row["direction"],
                confidence=float(row["confidence"]),
                prediction_time=row["time"],
            )

    async def get_unresolved(self) -> list[Prediction]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM fn_get_unresolved_predictions()")
            return [
                Prediction(
                    symbol=row["symbol"],
                    horizon=row["horizon"],
                    direction=row["direction"],
                    confidence=float(row["confidence"]),
                    prediction_time=row["time"],
                )
                for row in rows
            ]
