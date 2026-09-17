from __future__ import annotations

import asyncpg

from app.domain.alert import AlertConfig


class AlertConfigRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def get_for_user(self, user_id: str) -> list[AlertConfig]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM fn_get_alert_configs_for_user($1)", user_id)
            return [self._to_domain(row) for row in rows]

    async def get_matching_type(self, alert_type: str, symbol: str | None) -> list[AlertConfig]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM fn_get_matching_alert_configs($1, $2)",
                alert_type,
                symbol,
            )
            return [self._to_domain(row) for row in rows]

    @staticmethod
    def _to_domain(row) -> AlertConfig:
        return AlertConfig(
            user_id=str(row["user_id"]),
            symbol=row["symbol"],
            alert_type=row["alert_type"],
            threshold_value=float(row["min_confidence"]),
            horizons=list(row["horizons"]),
            channels=list(row["channels"]),
            is_enabled=row["is_active"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
