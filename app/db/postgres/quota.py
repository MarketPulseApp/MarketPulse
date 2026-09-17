import asyncpg

from app.domain.quota import APIQuota


class QuotaRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def get_all(self) -> list[APIQuota]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM fn_get_all_quotas();")
            return [
                APIQuota(
                    source_name=r["source"],
                    daily_used=r["daily_used"],
                    monthly_used=r["monthly_used"],
                    is_unlimited=r["is_unlimited"],
                    daily_limit=r["daily_limit"],
                    monthly_limit=r["monthly_limit"],
                    api_key=r["api_key"],
                )
                for r in rows
            ]

    async def get_by_source(self, source_name: str) -> APIQuota | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM fn_get_all_quotas() WHERE source = $1;", source_name
            )
            if not row:
                return None
            return APIQuota(
                source_name=row["source"],
                daily_used=row["daily_used"],
                monthly_used=row["monthly_used"],
                is_unlimited=row["is_unlimited"],
                daily_limit=row["daily_limit"],
                monthly_limit=row["monthly_limit"],
                api_key=row["api_key"],
            )

    async def update_quota(
        self,
        source_name: str,
        daily_limit: int | None,
        monthly_limit: int | None,
        api_key: str | None,
    ):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """UPDATE api_quotas
                   SET daily_limit = $1, monthly_limit = $2, api_key = $3, updated_at = NOW()
                   WHERE source = $4""",
                daily_limit,
                monthly_limit,
                api_key,
                source_name,
            )

    async def create_quota(
        self,
        source_name: str,
        daily_limit: int | None,
        monthly_limit: int | None,
        api_key: str | None,
    ):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO api_quotas (source, daily_limit, monthly_limit, api_key, is_unlimited)
                   VALUES ($1, $2, $3, $4, $5)
                   ON CONFLICT (source) DO UPDATE
                   SET daily_limit = EXCLUDED.daily_limit,
                       monthly_limit = EXCLUDED.monthly_limit,
                       api_key = EXCLUDED.api_key""",
                source_name,
                daily_limit,
                monthly_limit,
                api_key,
                (daily_limit is None and monthly_limit is None),
            )
