import asyncpg

from app.domain.system_settings import SystemSettings


class SystemSettingsRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def get_settings(self) -> SystemSettings:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, active_strategy, confidence_threshold FROM system_settings WHERE id = 1"
            )
            if row:
                return SystemSettings(**dict(row))
            return None

    async def update_settings(
        self, active_strategy: str, confidence_threshold: float
    ) -> SystemSettings:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO system_settings (id, active_strategy, confidence_threshold)
                VALUES (1, $1, $2)
                ON CONFLICT (id) DO UPDATE
                SET active_strategy = $1, confidence_threshold = $2
                RETURNING id, active_strategy, confidence_threshold
                """,
                active_strategy,
                confidence_threshold,
            )
            if row:
                return SystemSettings(**dict(row))
            return None
