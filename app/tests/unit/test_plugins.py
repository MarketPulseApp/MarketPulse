"""
tests/unit/test_plugins.py

Unit tests for the plugin registry (app/plugins/__init__.py).

Covers Phase 2.5.8:
  - load_all_plugins() discovers plugins in the datasources/ and delivery/ dirs
  - get_enabled_datasources() filters by feature flags
  - register_datasource() avoids duplicate registration
"""

from unittest.mock import MagicMock, patch

import pytest

from app.plugins import (
    _datasource_registry,
    _delivery_registry,
    get_enabled_datasources,
    load_all_plugins,
    register_datasource,
)
from app.plugins.datasources.base import DataSourcePlugin
from app.plugins.delivery.base import AlertDeliveryPlugin, AlertPayload, DeliveryResult

# Fixtures


class FakeDataSourcePlugin(DataSourcePlugin):
    """Minimal concrete datasource plugin for testing."""

    source_name = "test_source"
    source_type = "news"
    feature_flag = "datasource.test_source"

    async def fetch(self, symbols, since):
        return []

    def get_quota_info(self):
        return None


class AnotherFakeDataSourcePlugin(DataSourcePlugin):
    """Second datasource plugin to test multi-plugin scenarios."""

    source_name = "another_source"
    source_type = "price"
    feature_flag = "datasource.another_source"

    async def fetch(self, symbols, since):
        return []

    def get_quota_info(self):
        return None


class FakeDeliveryPlugin(AlertDeliveryPlugin):
    """Minimal concrete delivery plugin for testing."""

    channel_name = "test_channel"
    feature_flag = "delivery.test_channel"

    async def deliver(self, alert: AlertPayload, recipient: str) -> DeliveryResult:
        return DeliveryResult(success=True, channel=self.channel_name)


@pytest.fixture(autouse=True)
def clear_registries():
    """Reset both registries before each test to prevent state leaking between tests."""
    _datasource_registry.clear()
    _delivery_registry.clear()
    yield
    _datasource_registry.clear()
    _delivery_registry.clear()


# register_datasource()


class TestRegisterDatasource:
    def test_registers_plugin_by_source_name(self):
        plugin = FakeDataSourcePlugin()
        register_datasource(plugin)
        assert "test_source" in _datasource_registry

    def test_duplicate_registration_does_not_add_second_entry(self):
        plugin = FakeDataSourcePlugin()
        register_datasource(plugin)
        register_datasource(plugin)
        assert len(_datasource_registry) == 1

    def test_two_different_plugins_both_registered(self):
        register_datasource(FakeDataSourcePlugin())
        register_datasource(AnotherFakeDataSourcePlugin())
        assert len(_datasource_registry) == 2


# get_enabled_datasources()


class TestGetEnabledDatasources:
    def test_returns_plugin_when_flag_is_true(self):
        register_datasource(FakeDataSourcePlugin())
        flags = {"datasource.test_source": True}
        result = get_enabled_datasources(flags)
        assert len(result) == 1
        assert result[0].source_name == "test_source"

    def test_excludes_plugin_when_flag_is_false(self):
        register_datasource(FakeDataSourcePlugin())
        flags = {"datasource.test_source": False}
        result = get_enabled_datasources(flags)
        assert len(result) == 0

    def test_plugin_enabled_by_default_when_flag_absent(self):
        """If no flag exists for a plugin, it should be enabled by default."""
        register_datasource(FakeDataSourcePlugin())
        result = get_enabled_datasources({})
        assert len(result) == 1

    def test_filters_mixed_flags_correctly(self):
        register_datasource(FakeDataSourcePlugin())
        register_datasource(AnotherFakeDataSourcePlugin())
        flags = {
            "datasource.test_source": True,
            "datasource.another_source": False,
        }
        result = get_enabled_datasources(flags)
        assert len(result) == 1
        assert result[0].source_name == "test_source"


# load_all_plugins()


class TestLoadAllPlugins:
    def test_load_all_plugins_populates_datasource_registry(self):
        """
        load_all_plugins() should walk the datasources/ directory and register
        any concrete DataSourcePlugin subclasses it finds.
        We mock pkgutil.walk_packages to return our fake plugin module.
        """
        fake_module = MagicMock()
        fake_module.FakeDataSourcePlugin = FakeDataSourcePlugin

        with patch("app.plugins.pkgutil.walk_packages") as mock_walk:
            mock_walk.return_value = [(MagicMock(), "app.plugins.datasources.fake", False)]
            with patch("app.plugins.importlib.import_module", return_value=fake_module):
                load_all_plugins()

        assert "test_source" in _datasource_registry

    def test_load_all_plugins_skips_abstract_base_class(self):
        """
        load_all_plugins() must not try to instantiate DataSourcePlugin itself
        since it is abstract and has no source_name.
        """
        fake_module = MagicMock()
        fake_module.DataSourcePlugin = DataSourcePlugin

        with patch("app.plugins.pkgutil.walk_packages") as mock_walk:
            mock_walk.return_value = [(MagicMock(), "app.plugins.datasources.base", False)]
            with patch("app.plugins.importlib.import_module", return_value=fake_module):
                load_all_plugins()

        assert len(_datasource_registry) == 0
