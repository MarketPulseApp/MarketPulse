from __future__ import annotations

from app.domain.alert import Alert, DeliveryResult
from app.plugins.delivery.base import AlertDeliveryPlugin


class DiscordDeliveryPlugin(AlertDeliveryPlugin):
    channel_name = "discord"
    feature_flag = "delivery.discord"

    async def deliver(self, alert: Alert, recipient: str) -> DeliveryResult:
        raise NotImplementedError("Discord delivery not yet implemented")
