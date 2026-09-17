import redis.asyncio as redis

FLAG_PREFIX = "flag:"


class FeatureFlagRepository:
    def __init__(self, client: redis.Redis) -> None:
        self.client = client

    async def get(self, flag: str) -> bool | None:
        raw = await self.client.get(f"{FLAG_PREFIX}{flag}")
        if raw is None:
            return None
        return raw.decode() == "1"

    async def set(self, flag: str, value: bool) -> None:
        await self.client.set(f"{FLAG_PREFIX}{flag}", "1" if value else "0")

    async def get_all(self) -> dict[str, bool]:
        keys = await self.client.keys(f"{FLAG_PREFIX}*")
        if not keys:
            return {}

        raws = await self.client.mget(*keys)
        return {
            key.decode().removeprefix(FLAG_PREFIX): raw.decode() == "true"
            for key, raw in zip(keys, raws)
            if raw is not None
        }

    async def set_many(self, flags: dict[str, bool]) -> None:
        async with self.client.pipeline() as pipe:
            for flag, value in flags.items():
                pipe.set(f"{FLAG_PREFIX}{flag}", "1" if value else "0")
            await pipe.execute()
