from collections.abc import AsyncGenerator

import redis.asyncio as redis


class PubSubRepository:
    def __init__(self, client: redis.Redis) -> None:
        self.client = client

    async def publish(self, channel: str, event: bytes) -> None:
        await self.client.publish(channel, event)

    async def subscribe(self, channel: str) -> AsyncGenerator[bytes, None]:
        pubsub = self.client.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield message["data"]
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
