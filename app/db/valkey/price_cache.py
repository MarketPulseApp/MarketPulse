import json

import redis.asyncio as redis

KEY_PREFIX = "price:cache:"
TTL_SECONDS = 60


class PriceCacheRepository:
    def __init__(self, client: redis.Redis) -> None:
        self.client = client

    async def set(self, symbol: str, price_data: dict) -> None:
        await self.client.set(
            f"{KEY_PREFIX}{symbol}",
            json.dumps(price_data),
            ex=TTL_SECONDS,
        )

    async def get(self, symbol: str) -> dict | None:
        raw = await self.client.get(f"{KEY_PREFIX}{symbol}")
        if raw is None:
            return None
        return json.loads(raw)

    async def delete(self, symbol: str) -> None:
        await self.client.delete(f"{KEY_PREFIX}{symbol}")

    async def set_many(self, prices: dict[str, dict]) -> None:
        async with self.client.pipeline() as pipe:
            for symbol, price_data in prices.items():
                pipe.set(
                    f"{KEY_PREFIX}{symbol}",
                    json.dumps(price_data),
                    ex=TTL_SECONDS,
                )
            await pipe.execute()

    async def get_many(self, symbols: list[str]) -> dict[str, dict]:
        keys = [f"{KEY_PREFIX}{s}" for s in symbols]
        raws = await self.client.mget(*keys)
        return {symbol: json.loads(raw) for symbol, raw in zip(symbols, raws) if raw is not None}
