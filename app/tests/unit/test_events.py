"""
tests/unit/test_events.py

Unit tests for the event publisher (app/events/publisher.py).

Covers Phase 2.5.9:
  - Events serialise correctly with MessagePack
  - The correct Valkey channel name is used
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import msgpack
import pytest

from app.events.publisher import CHANNEL, publish_event
from app.events.types import (
    BreakingNewsEvent,
    PredictionChangedEvent,
    QuotaWarningEvent,
    UnusualVolumeEvent,
)

# Helpers


def unpack(payload: bytes) -> dict:
    """Deserialise a MessagePack payload back to a dict for assertion."""
    return msgpack.unpackb(payload, raw=False)


# Channel name


class TestChannelName:
    def test_channel_constant_is_correct(self):
        """The publisher must use the agreed channel name."""
        assert CHANNEL == "marketpulse:events"


# Serialisation


class TestEventSerialisation:
    @pytest.mark.asyncio
    async def test_prediction_changed_event_serialises_all_fields(self):
        event = PredictionChangedEvent(
            symbol="AAPL",
            old_direction="FLAT",
            new_direction="UP",
            confidence=87.5,
            horizon="1d",
        )

        captured = {}

        async def fake_publish(channel, payload):
            captured["channel"] = channel
            captured["payload"] = payload

        with patch("app.events.publisher.redis") as mock_redis:
            mock_redis.publish = AsyncMock(side_effect=fake_publish)
            await publish_event(event)

        data = unpack(captured["payload"])
        assert data["event_type"] == "prediction_changed"
        assert data["symbol"] == "AAPL"
        assert data["old_direction"] == "FLAT"
        assert data["new_direction"] == "UP"
        assert data["confidence"] == 87.5
        assert data["horizon"] == "1d"

    @pytest.mark.asyncio
    async def test_unusual_volume_event_serialises_all_fields(self):
        event = UnusualVolumeEvent(
            symbol="TSLA",
            volume=5_000_000,
            avg_volume=1_000_000,
            multiplier=5.0,
        )

        captured = {}

        async def fake_publish(channel, payload):
            captured["payload"] = payload

        with patch("app.events.publisher.redis") as mock_redis:
            mock_redis.publish = AsyncMock(side_effect=fake_publish)
            await publish_event(event)

        data = unpack(captured["payload"])
        assert data["event_type"] == "unusual_volume"
        assert data["symbol"] == "TSLA"
        assert data["multiplier"] == 5.0

    @pytest.mark.asyncio
    async def test_timestamp_is_serialised_as_iso_string(self):
        """datetime fields must be converted to ISO strings before packing."""
        ts = datetime(2026, 1, 15, 9, 30, 0, tzinfo=UTC)
        event = PredictionChangedEvent(
            symbol="AAPL",
            old_direction="FLAT",
            new_direction="UP",
            confidence=80.0,
            horizon="1d",
            timestamp=ts,
        )

        captured = {}

        async def fake_publish(channel, payload):
            captured["payload"] = payload

        with patch("app.events.publisher.redis") as mock_redis:
            mock_redis.publish = AsyncMock(side_effect=fake_publish)
            await publish_event(event)

        data = unpack(captured["payload"])
        assert isinstance(data["timestamp"], str)
        assert data["timestamp"] == ts.isoformat()

    @pytest.mark.asyncio
    async def test_none_timestamp_is_handled(self):
        """Events with no timestamp set should not raise."""
        event = PredictionChangedEvent(
            symbol="AAPL",
            old_direction="FLAT",
            new_direction="UP",
            confidence=80.0,
            horizon="1d",
            timestamp=None,
        )

        with patch("app.events.publisher.redis") as mock_redis:
            mock_redis.publish = AsyncMock()
            await publish_event(event)

        mock_redis.publish.assert_called_once()


# Channel routing


class TestChannelRouting:
    @pytest.mark.asyncio
    async def test_publish_uses_correct_channel(self):
        """All events must go to marketpulse:events regardless of event type."""
        events = [
            PredictionChangedEvent(symbol="AAPL"),
            UnusualVolumeEvent(symbol="TSLA"),
            BreakingNewsEvent(symbol="MSFT"),
        ]

        for event in events:
            with patch("app.events.publisher.redis") as mock_redis:
                mock_redis.publish = AsyncMock()
                await publish_event(event)
                call_args = mock_redis.publish.call_args
                assert (
                    call_args[0][0] == "marketpulse:events"
                ), f"{type(event).__name__} published to wrong channel"

    @pytest.mark.asyncio
    async def test_publish_called_exactly_once_per_event(self):
        event = QuotaWarningEvent(source_name="newsapi", percent_used=90.0)

        with patch("app.events.publisher.redis") as mock_redis:
            mock_redis.publish = AsyncMock()
            await publish_event(event)
            assert mock_redis.publish.call_count == 1
