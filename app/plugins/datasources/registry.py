import json

from app.infrastructure import valkey
from app.plugins.datasources.base import DataSourcePlugin
from app.plugins.datasources.generic import GenericRestAPIPlugin, GenericRSSPlugin
from app.plugins.datasources.middleware import QuotaMiddleware


async def get_enabled_datasources() -> list[DataSourcePlugin]:
    """
    Reads Valkey for registered data sources and dynamically instantiates them.
    A registered source in Valkey might look like:
    Key: "datasource:custom:my_news_api"
    Value: {"type": "rest_api", "url": "...", "token": "...", "daily_limit": 100}
    """
    plugins = []

    if valkey.redis is None:
        return plugins

    # We scan for dynamically added sources
    cursor = 0
    while True:
        cursor, keys = await valkey.redis.scan(cursor, match="datasource:custom:*")
        for key in keys:
            try:
                data_str = await valkey.redis.get(key)
                if not data_str:
                    continue

                data = json.loads(data_str)
                is_enabled = data.get("enabled", True)
                if not is_enabled:
                    continue

                source_name = key.split(":")[-1]

                if data["type"] == "rest_api":
                    plugin = GenericRestAPIPlugin(
                        source_name=source_name,
                        record_type=data.get("record_type", "data"),
                        base_url=data["url"],
                        api_token=data.get("token", ""),
                        daily_limit=data.get("daily_limit"),
                    )
                elif data["type"] == "rss":
                    plugin = GenericRSSPlugin(source_name=source_name, feed_url=data["url"])
                else:
                    continue

                # Wrap with quota middleware
                wrapped_plugin = QuotaMiddleware.wrap(plugin)
                plugins.append(wrapped_plugin)
            except Exception as e:
                import logging

                logging.getLogger(__name__).error(f"Error loading plugin {key}: {e}")

        if int(cursor) == 0:
            break

    # Normally we'd also load static plugins here if they are enabled via feature flags
    # ...

    return plugins


async def register_datasource(source_name: str, config: dict):
    """
    Registers a new data source dynamically via the UI.
    """
    if valkey.redis:
        key = f"datasource:custom:{source_name}"
        await valkey.redis.set(key, json.dumps(config))
