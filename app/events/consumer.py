import msgpack

from app.db.alert_configs import get_matching_configs
from app.infrastructure.valkey import redis
from app.plugins import get_enabled_delivery_plugins


async def run_alert_consumer():
    async with redis.pubsub() as pubsub:
        await pubsub.subscribe("marketpulse:events")
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            event = msgpack.unpackb(message["data"], raw=False)
            await evaluate_and_dispatch(event)


async def evaluate_and_dispatch(event: dict) -> None:
    configs = await get_matching_configs(event["event_type"], event.get("symbol"))
    plugins = get_enabled_delivery_plugins()
    for config in configs:
        for channel in config.channels:
            plugin = plugins.get(channel)
            if plugin:
                await plugin.deliver(Alert.from_event(event, config), config.user)  # noqa: F821
