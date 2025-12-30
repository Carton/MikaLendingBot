"""
Tests for PluginsManager module.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from lendingbot.modules import PluginsManager


@pytest.fixture
def plugins_manager():
    # Reset globals
    PluginsManager.active_plugins = []
    PluginsManager.log = None
    return PluginsManager


class TestPluginsManager:
    def test_init_and_lifecycle(self, plugins_manager):
        mock_config = Mock()
        mock_config.get_plugins_config.return_value = ["TestPlugin"]

        mock_log = MagicMock()
        mock_api = Mock()
        notify_conf = {}

        # Mock the plugins package to contain our TestPlugin
        class MockPlugin:
            def __init__(self, _cfg, _api, _log, _notify):
                self.on_bot_init_called = False
                self.before_lending_called = False
                self.after_lending_called = False
                self.on_bot_stop_called = False

            def on_bot_init(self):
                self.on_bot_init_called = True

            def before_lending(self):
                self.before_lending_called = True

            def after_lending(self):
                self.after_lending_called = True

            def on_bot_stop(self):
                self.on_bot_stop_called = True

        with patch("lendingbot.plugins.TestPlugin", MockPlugin, create=True):
            plugins_manager.init(mock_config, mock_api, mock_log, notify_conf)

            assert len(plugins_manager.active_plugins) == 1
            plugin = plugins_manager.active_plugins[0]
            assert plugin.on_bot_init_called is True

            plugins_manager.before_lending()
            assert plugin.before_lending_called is True

            plugins_manager.after_lending()
            assert plugin.after_lending_called is True

            plugins_manager.on_bot_stop()
            assert plugin.on_bot_stop_called is True

    def test_plugin_not_found(self, plugins_manager):
        mock_config = Mock()
        mock_config.get_plugins_config.return_value = ["NonExistentPlugin"]
        mock_log = MagicMock()

        plugins_manager.init(mock_config, Mock(), mock_log, {})

        assert len(plugins_manager.active_plugins) == 0
        mock_log.log_error.assert_called_with(
            "Plugin NonExistentPlugin not found in plugins folder"
        )

    def test_plugin_error_handling(self, plugins_manager):
        mock_config = Mock()
        mock_config.get_plugins_config.return_value = ["ErrorPlugin"]
        mock_log = MagicMock()

        class ErrorPlugin:
            def __init__(self, *args, **kwargs):
                pass

            def on_bot_init(self):
                raise Exception("Init Error")

            def before_lending(self):
                raise Exception("Before Error")

        with patch("lendingbot.plugins.ErrorPlugin", ErrorPlugin, create=True):
            plugins_manager.init(mock_config, Mock(), mock_log, {})
            assert len(plugins_manager.active_plugins) == 0  # Should not be added if init fails
            mock_log.log_error.assert_called()

            # Manually add to test lifecycle error handling
            instance = ErrorPlugin()
            plugins_manager.active_plugins = [instance]
            plugins_manager.before_lending()
            mock_log.log_error.assert_called()
