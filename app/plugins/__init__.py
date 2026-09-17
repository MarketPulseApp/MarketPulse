import importlib
import pkgutil
from pathlib import Path

from app.plugins.datasources.base import DataSourcePlugin
from app.plugins.delivery.base import AlertDeliveryPlugin

_datasource_registry: dict[str, DataSourcePlugin] = {}
_delivery_registry: dict[str, AlertDeliveryPlugin] = {}


def register_datasource(plugin: DataSourcePlugin) -> None:
    if plugin.source_name in _datasource_registry:
        return
    _datasource_registry[plugin.source_name] = plugin


def register_delivery(plugin: AlertDeliveryPlugin) -> None:
    _delivery_registry[plugin.channel_name] = plugin


def load_all_plugins() -> None:
    """Auto-discover and load all plugins in the datasources/ and delivery/ directories."""
    for pkg, module_name, _ in pkgutil.walk_packages(
        [str(Path(__file__).parent / "datasources")], prefix="app.plugins.datasources."
    ):
        module = importlib.import_module(module_name)
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, DataSourcePlugin)
                and attr is not DataSourcePlugin
            ):
                instance = attr()
                register_datasource(instance)

    for pkg, module_name, _ in pkgutil.walk_packages(
        [str(Path(__file__).parent / "delivery")], prefix="app.plugins.delivery."
    ):
        module = importlib.import_module(module_name)
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, AlertDeliveryPlugin)
                and attr is not AlertDeliveryPlugin
            ):
                delivery_instance = attr()
                register_delivery(delivery_instance)


def get_enabled_datasources(flags: dict[str, bool]) -> list[DataSourcePlugin]:
    return [
        p
        for p in _datasource_registry.values()
        if (flags.get(p.feature_flag, True))  # default enabled if no flag
    ]


def get_enabled_delivery_plugins(
    flags: dict[str, bool] | None = None,
) -> dict[str, AlertDeliveryPlugin]:
    flags = flags or {}
    return {name: p for name, p in _delivery_registry.items() if flags.get(p.feature_flag, True)}
