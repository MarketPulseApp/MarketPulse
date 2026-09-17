import asyncpg

from app.domain.quota import APIQuota


class QuotaRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def increment(self, source: str, daily: bool) -> None:
        """
        daily = True increments daily_used, otherwise, increments monthly_used
        is quota is set as is_unlimited x
        """
        async with self.pool.acquire() as conn:
            await conn.execute("SELECT fn_increment_quota($1, $2)", source, daily)

    async def get_all(self) -> list[APIQuota]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM fn_get_all_quotas()")
            return [
                APIQuota(
                    source_name=row["source"],
                    daily_used=row["daily_used"],
                    monthly_used=row["monthly_used"],
                    is_unlimited=row["is_unlimited"],
                    low_threshold=row["low_threshold"],
                    daily_limit=row["daily_limit"],
                    monthly_limit=row["monthly_limit"],
                    last_reset_daily=row["last_reset_daily"],
                    last_reset_monthly=row["last_reset_monthly"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]

    async def reset(self, source: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("SELECT fn_reset_quota($1)", source)
