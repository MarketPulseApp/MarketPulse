from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from app.events.types import BaseEvent


@dataclass
class AlertConfig:
    user_id: str
    alert_type: str
    channels: list[str]
    symbol: str | None = None
    is_enabled: bool = True
    threshold_value: float | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self):
        if len(self.channels) == 0:
            raise ValueError


@dataclass
class Alert:
    alert_type: str
    symbol: str | None
    message: str
    channels: list[str]
    threshold_value: float | None
    current_value: float | None
    triggered_at: datetime | None = None

    def should_fire(self) -> bool:
        if self.threshold_value is None:
            return True
        if self.current_value is None:
            return True
        return self.current_value >= self.threshold_value

    @classmethod
    def from_event(cls, event: BaseEvent, config: AlertConfig) -> "Alert":
        symbol = getattr(event, "symbol", None)

        current_value = (
            getattr(event, "confidence", None)
            or getattr(event, "percent_used", None)
            or getattr(event, "multiplier", None)
        )

        message = f"{event.event_type} alert triggered"
        if symbol:
            message += f" for {symbol}"

        return cls(
            alert_type=config.alert_type,
            symbol=symbol,
            message=message,
            channels=config.channels,
            threshold_value=config.threshold_value,
            current_value=current_value,
            triggered_at=datetime.now(UTC),
        )


@dataclass
class NotificationPreference:
    user_id: str
    channel: Literal["browser", "mobile", "email", "sms", "discord", "voice"]
    is_enabled: bool


@dataclass
class DeliveryResult:
    """
    Outcome of a single delivery attempt.
    Never raises - a failed delivery returns success=False with an error message.
    """

    success: bool
    channel: str
    error: str | None = None
    delivered_at: datetime | None = None
