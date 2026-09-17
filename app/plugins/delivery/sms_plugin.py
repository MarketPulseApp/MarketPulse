from __future__ import annotations

from app.domain.alert import Alert, DeliveryResult
from app.plugins.delivery.base import AlertDeliveryPlugin


class SMSDeliveryPlugin(AlertDeliveryPlugin):
    channel_name = "sms"
    feature_flag = "delivery.sms"

    async def deliver(self, alert: Alert, recipient: str) -> DeliveryResult:
        raise NotImplementedError("SMS delivery not yet implemented")
