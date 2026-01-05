"""
Tests for PluginsManager module using Dependency Injection.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from lendingbot.modules.PluginsManager import PluginsManager
from lendingbot.modules.Configuration import RootConfig, PluginsConfig


@pytest.fixture
def mock_config():
    # Setup config to enable plugins
    return RootConfig(
        plugins=PluginsConfig(
            account_stats={"enabled": True},
            charts={"enabled": True}
        )
    )

@pytest.fixture
def mock_log():
    return MagicMock()

@pytest.fixture
def mock_api():
    return Mock()

class TestPluginsManager:
    def test_init_and_lifecycle(self, mock_config, mock_api, mock_log):
        # Create mocks for plugin classes
        MockAccountStats = MagicMock()
        MockCharts = MagicMock()
        
        # Setup mock instances
        account_stats_instance = MockAccountStats.return_value
        charts_instance = MockCharts.return_value

        with patch("lendingbot.plugins.AccountStats", MockAccountStats):
            with patch("lendingbot.plugins.Charts", MockCharts):
                manager = PluginsManager(mock_config, mock_api, mock_log)

                # Check initialization
                assert len(manager.active_plugins) == 2
                assert account_stats_instance.on_bot_init.called
                assert charts_instance.on_bot_init.called

                # Check lifecycle methods
                manager.before_lending()
                assert account_stats_instance.before_lending.called
                assert charts_instance.before_lending.called

                manager.after_lending()
                assert account_stats_instance.after_lending.called
                assert charts_instance.after_lending.called

                manager.on_bot_stop()
                assert account_stats_instance.on_bot_stop.called
                assert charts_instance.on_bot_stop.called

    def test_plugin_init_error(self, mock_config, mock_api, mock_log):
        # Simulate an error during plugin initialization
        MockAccountStats = MagicMock()
        MockAccountStats.side_effect = Exception("Init failed")

        with patch("lendingbot.plugins.AccountStats", MockAccountStats):
            # Only enable AccountStats
            mock_config.plugins.charts["enabled"] = False
            
            manager = PluginsManager(mock_config, mock_api, mock_log)
            
            # Should handle exception and log error, not crash
            assert len(manager.active_plugins) == 0
            mock_log.log_error.assert_called()

    def test_lifecycle_error_handling(self, mock_config, mock_api, mock_log):
        MockAccountStats = MagicMock()
        instance = MockAccountStats.return_value
        # Simulate error in lifecycle method
        instance.before_lending.side_effect = Exception("Runtime error")

        with patch("lendingbot.plugins.AccountStats", MockAccountStats):
            mock_config.plugins.charts["enabled"] = False
            
            manager = PluginsManager(mock_config, mock_api, mock_log)
            assert len(manager.active_plugins) == 1

            # Should catch exception and log error
            manager.before_lending()
            mock_log.log_error.assert_called()

    def test_plugin_not_found(self, mock_config, mock_api, mock_log):
        # Patch the plugins module where PluginsManager imports it
        with patch("lendingbot.modules.PluginsManager.plugins") as mock_plugins_mod:
            # Make accessing AccountStats raise AttributeError
            del mock_plugins_mod.AccountStats
            
            # Disable charts to focus on AccountStats
            mock_config.plugins.charts["enabled"] = False
            
            manager = PluginsManager(mock_config, mock_api, mock_log)
            
            assert len(manager.active_plugins) == 0
            mock_log.log_error.assert_called_with("Plugin AccountStats not found in plugins folder")
