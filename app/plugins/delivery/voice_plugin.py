from __future__ import annotations

from app.domain.alert import Alert, DeliveryResult
from app.plugins.delivery.base import AlertDeliveryPlugin


class VoiceDeliveryPlugin(AlertDeliveryPlugin):
    channel_name = "voice"
    feature_flag = "delivery.voice"

    async def deliver(self, alert: Alert, recipient: str) -> DeliveryResult:
        raise NotImplementedError("Voice call delivery not yet implemented")
