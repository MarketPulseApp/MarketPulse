import json
from unittest.mock import AsyncMock, patch

import pytest

from app.plugins.datasources import registry
from app.plugins.datasources.generic import GenericRestAPIPlugin, GenericRSSPlugin


@pytest.mark.asyncio
async def test_register_datasource():
    with patch("app.plugins.datasources.registry.valkey") as mock_valkey:
        mock_valkey.redis = AsyncMock()

        config = {"type": "rest_api", "url": "https://api.example.com", "token": "secret"}
        await registry.register_datasource("my_source", config)

        mock_valkey.redis.set.assert_called_once_with(
            "datasource:custom:my_source", json.dumps(config)
        )


@pytest.mark.asyncio
async def test_get_enabled_datasources():
    with patch("app.plugins.datasources.registry.valkey") as mock_valkey:
        mock_redis = AsyncMock()
        mock_valkey.redis = mock_redis

        # Simulating redis scan returning a cursor and a list of keys
        mock_redis.scan.side_effect = [
            (
                "0",
                [
                    "datasource:custom:test_rest",
                    "datasource:custom:test_rss",
                    "datasource:custom:disabled_source",
                    "datasource:custom:invalid_type",
                ],
            )
        ]

        async def mock_get(key):
            if key == "datasource:custom:test_rest":
                return json.dumps(
                    {
                        "enabled": True,
                        "type": "rest_api",
                        "url": "https://api.example.com",
                        "token": "secret123",
                        "daily_limit": 100,
                    }
                )
            elif key == "datasource:custom:test_rss":
                return json.dumps(
                    {"enabled": True, "type": "rss", "url": "https://rss.example.com"}
                )
            elif key == "datasource:custom:disabled_source":
                return json.dumps(
                    {
                        "enabled": False,
                        "type": "rest_api",
                        "url": "https://api.example.com/2",
                        "token": "secret",
                    }
                )
            elif key == "datasource:custom:invalid_type":
                return json.dumps({"enabled": True, "type": "unknown_type"})
            return None

        mock_redis.get.side_effect = mock_get

        plugins = await registry.get_enabled_datasources()

        # Only test_rest and test_rss should be returned
        assert len(plugins) == 2

        rest_plugin = next((p for p in plugins if p.source_name == "test_rest"), None)
        rss_plugin = next((p for p in plugins if p.source_name == "test_rss"), None)

        assert rest_plugin is not None
        assert isinstance(rest_plugin, GenericRestAPIPlugin)
        assert rest_plugin.base_url == "https://api.example.com"
        assert rest_plugin.api_token == "secret123"
        assert rest_plugin._quota_info.daily_limit == 100
        assert rest_plugin.fetch.__name__ == "wrapped_fetch"  # Wrapped by QuotaMiddleware

        assert rss_plugin is not None
        assert isinstance(rss_plugin, GenericRSSPlugin)
        assert rss_plugin.feed_url == "https://rss.example.com"
        assert rss_plugin.fetch.__name__ == "wrapped_fetch"  # Wrapped by QuotaMiddleware
