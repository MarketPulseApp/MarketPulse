from __future__ import annotations

from app.domain.alert import Alert, DeliveryResult
from app.plugins.delivery.base import AlertDeliveryPlugin


class BrowserPushDeliveryPlugin(AlertDeliveryPlugin):
    channel_name = "browser_push"
    feature_flag = "delivery.browser_push"

    async def deliver(self, alert: Alert, recipient: str) -> DeliveryResult:
        raise NotImplementedError("Browser push delivery not yet implemented")
