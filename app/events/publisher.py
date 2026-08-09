from datetime import datetime

import msgpack

from app.infrastructure.valkey import redis

CHANNEL = "marketpulse:events"


async def publish_event(event) -> None:
    raw = {"event_type": event.event_type, **event.__dict__}
    payload = msgpack.packb(
        {k: v.isoformat() if isinstance(v, datetime) else v for k, v in raw.items()},
        use_bin_type=True,
    )
    await redis.publish(CHANNEL, payload)
