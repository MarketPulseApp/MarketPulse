import redis.asyncio as redis

BLOCKLIST_PREFIX = "blocklist:"


class SessionRepository:
    def __init__(self, client: redis.Redis) -> None:
        self.client = client

    async def create(self, jti: str, ttl_seconds: int) -> None:
        await self.client.set(f"{BLOCKLIST_PREFIX}{jti}", 1, ex=ttl_seconds)

    async def is_blocked(self, jti: str) -> bool:
        return await self.client.exists(f"{BLOCKLIST_PREFIX}{jti}") == 1

    async def invalidate(self, jti: str) -> None:
        return await self.client.delete(f"{BLOCKLIST_PREFIX}{jti}")
