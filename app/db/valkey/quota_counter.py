import redis.asyncio as redis

DAILY_PREFIX = "quota:daily:"
MONTHLY_PREFIX = "quota:monthly:"


class QuotaCounterRepository:
    def __init__(self, client: redis.Redis) -> None:
        self.client = client

    def _key(self, source: str, daily: bool) -> str:
        return f"{DAILY_PREFIX}{source}" if daily else f"{MONTHLY_PREFIX}{source}"

    async def increment(self, source: str, daily: bool) -> int:
        return await self.client.incr(self._key(source, daily))

    async def get_count(self, source: str, daily: bool) -> int:
        raw = await self.client.get(self._key(source, daily))
        return int(raw) if raw is not None else 0

    async def reset(self, source: str, daily: bool) -> None:
        await self.client.set(self._key(source, daily), 0)

    async def get_all_counts(self, sources: list[str]) -> dict[str, dict]:
        daily_keys = [f"{DAILY_PREFIX}{s}" for s in sources]
        monthly_keys = [f"{MONTHLY_PREFIX}{s}" for s in sources]
        daily_raws = await self.client.mget(*daily_keys)
        monthly_raws = await self.client.mget(*monthly_keys)
        return {
            source: {
                "daily": int(d) if d is not None else 0,
                "monthly": int(m) if m is not None else 0,
            }
            for source, d, m, in zip(sources, daily_raws, monthly_raws)
        }
