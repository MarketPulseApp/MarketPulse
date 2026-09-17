from __future__ import annotations

from app.domain.alert import Alert, DeliveryResult
from app.plugins.delivery.base import AlertDeliveryPlugin


class MobilePushDeliveryPlugin(AlertDeliveryPlugin):
    channel_name = "mobile_push"
    feature_flag = "delivery.mobile_push"

    async def deliver(self, alert: Alert, recipient: str) -> DeliveryResult:
        raise NotImplementedError("Mobile push delivery not yet implemented")
