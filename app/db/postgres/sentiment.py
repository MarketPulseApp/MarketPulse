import asyncpg

from app.core.config import settings
from app.domain.sentiment import SentimentScore


# TODO: Remove in Phase 5
async def create_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=settings.POSTGRES_DATABASE,
    )


class SentimentRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def insert_daily(self, score: SentimentScore) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "SELECT fn_insert_sentiment($1, $2, $3, $4, $5, $6, $7)",
                score.recorded_at,
                score.symbol,
                score.source_type,
                score.source_name,
                score.score,
                score.article_count,
                score.post_count,
            )

    async def get_trend(self, symbol: str, days: int) -> list[SentimentScore]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM fn_get_sentiment_trend($1, $2)", symbol, days)
            return [
                SentimentScore(
                    recorded_at=row["time"],
                    symbol=row["symbol"],
                    source_name=row["source_name"],
                    source_type=row["source_type"],
                    score=row["score"],
                    article_count=row["article_count"],
                    post_count=row["post_count"],
                )
                for row in rows
            ]
