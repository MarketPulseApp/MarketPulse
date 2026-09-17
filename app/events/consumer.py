from datetime import UTC, datetime

import asyncpg
import msgpack

from app.db.postgres.alert_config import AlertConfigRepository
from app.domain.alert import Alert
from app.infrastructure.valkey import redis
from app.plugins import get_enabled_delivery_plugins


async def run_alert_consumer(pool: asyncpg.Pool) -> None:
    assert redis is not None
    async with redis.pubsub() as pubsub:
        await pubsub.subscribe("marketpulse:events")
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            event = msgpack.unpackb(message["data"], raw=False)
            await evaluate_and_dispatch(event, pool)


async def evaluate_and_dispatch(event: dict, pool: asyncpg.Pool) -> None:
    repo = AlertConfigRepository(pool)
    configs = await repo.get_matching_type(event["event_type"], event.get("symbol"))
    plugins = get_enabled_delivery_plugins()
    for config in configs:
        for channel in config.channels:
            plugin = plugins.get(channel)
            if plugin:
                alert = Alert(
                    alert_type=event["event_type"],
                    symbol=event.get("symbol"),
                    message=f"{event['event_type']} alert triggered"
                    + (f" for {event['symbol']}" if event.get("symbol") else ""),
                    channels=config.channels,
                    threshold_value=config.threshold_value,
                    current_value=(
                        event.get("confidence")
                        or event.get("percent_used")
                        or event.get("multiplier")
                    ),
                    triggered_at=datetime.now(UTC),
                )
                if not alert.should_fire():
                    continue
                await plugin.deliver(alert, config.user_id)
