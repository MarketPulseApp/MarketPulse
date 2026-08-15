from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from app.domain.alert import DeliveryResult


@dataclass
class AlertPayload:
    """
    Minimal alert representation passed to every delivery plugin.
    Will be replaced by app.domain.alert.Alert in Phase 3.4 -
    at that point update the type hit in deliver() accordingly.
    """

    alert_id: str
    title: str
    body: str
    severity: str  # "info" | "warning" | "critical"
    triggered_at: datetime
    symbol: str | None = None
    metadata: dict = field(default_factory=dict)


class AlertDeliveryPlugin(ABC):
    """
    Abstract base fore alert delivery channels (email, Discord, SMS, push, etc.).

    Subclasses must set:
        channel_name - unique string key used in the registry and alert configs
        feature_flag - e.g. "delivery.email"; checked before dispatch

    Subclasses must implement:
        deliver() - send the alert; must not raise
    """

    channel_name: str
    feature_flag: str

    @abstractmethod
    async def deliver(self, alert: AlertPayload, recipient: str) -> DeliveryResult:
        """
        Send `alert` to `recipient`.

        recipient is channel-specific:
            - email -> "user@example.com"
            - SMS -> "+15551234567"
            - Discord -> user ID or webhook URL
            - push -> OneSignal player_id

        Must never raise. Catch all exceptions and return
        DeliveryResult(success=False, channel=self.channel_name, error=str(exc)).
        """
        pass

    async def health_check(self) -> bool:
        """
        Return True if the delivery channel is reachable.
        Default implementation always returns True - override for real checks.
        """
        return True
