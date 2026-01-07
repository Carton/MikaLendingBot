from unittest.mock import MagicMock, patch

from lendingbot.modules.Orchestrator import BotOrchestrator


class TestOrchestrator:
    def test_orchestrator_instantiation(self):
        """Test that the orchestrator can be instantiated with basic arguments."""
        orchestrator = BotOrchestrator(config_path="config.toml", dry_run=True)
        assert str(orchestrator.config_path) == "config.toml"
        assert orchestrator.dry_run is True

    @patch("lendingbot.modules.Configuration.load_config")
    @patch("lendingbot.modules.Orchestrator.Logger")
    @patch("lendingbot.modules.Orchestrator.ExchangeApiFactory.createApi")
    @patch("lendingbot.modules.Lending.LendingEngine")
    @patch("lendingbot.modules.PluginsManager.PluginsManager")
    def test_orchestrator_initialization(
        self, mock_pm, mock_le, mock_api, mock_logger, mock_load_config
    ):
        """Test the initialization sequence (loading config, api, etc)."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.bot.json_file = "bot.json"
        mock_config.bot.json_log_size = 2000
        mock_config.api.exchange.value = "poloniex"
        mock_config.bot.label = "TestBot"
        mock_config.plugins.market_analysis.analyse_currencies = False
        mock_config.bot.web.enabled = False

        mock_load_config.return_value = mock_config

        orchestrator = BotOrchestrator(config_path="config.toml", dry_run=True)
        orchestrator.initialize()

        # Verify config loaded
        assert mock_load_config.call_count == 1
        args, _ = mock_load_config.call_args
        assert str(args[0]) == "config.toml"

        # Verify components initialized
        mock_logger.assert_called()
        mock_api.assert_called()
        mock_le.assert_called()
        mock_pm.assert_called()

    @patch("lendingbot.modules.Orchestrator.Data")
    @patch("lendingbot.modules.Orchestrator.sys.stdout")
    @patch("lendingbot.modules.Orchestrator.time.time")
    def test_orchestrator_step(self, mock_time, _mock_stdout, mock_data):
        """Test a single step of the main loop."""
        orchestrator = BotOrchestrator(config_path="config.toml", dry_run=True)

        # Manually inject mocks for components to avoid calling initialize()
        orchestrator.config = MagicMock()
        orchestrator.config.bot.output_currency = "BTC"
        orchestrator.config.bot.web.enabled = False
        orchestrator.config.bot.period_inactive = 60

        orchestrator.log = MagicMock()
        orchestrator.engine = MagicMock()
        orchestrator.plugins_manager = MagicMock()

        # Setup initial state
        orchestrator.engine.lending_paused = False
        orchestrator.engine.last_lending_status = False  # No change
        mock_time.return_value = 1000
        orchestrator.last_summary_time = 0

        # Execute step
        orchestrator.step()

        # Verify interactions
        mock_data.update_conversion_rates.assert_called_with("BTC", False)

        # Verify lending cycle
        orchestrator.plugins_manager.before_lending.assert_called_once()
        orchestrator.engine.transfer_balances.assert_called_once()
        orchestrator.engine.cancel_all.assert_called_once()
        orchestrator.engine.lend_all.assert_called_once()
        orchestrator.plugins_manager.after_lending.assert_called_once()

        # Verify logging
        orchestrator.log.persistStatus.assert_called_once()

    @patch("lendingbot.modules.Orchestrator.os._exit")
    def test_orchestrator_stop(self, mock_exit):
        """Test the stop method."""
        orchestrator = BotOrchestrator(config_path="config.toml")
        orchestrator.web_server = MagicMock()
        orchestrator.plugins_manager = MagicMock()
        orchestrator.log = MagicMock()

        orchestrator.stop()

        orchestrator.web_server.stop.assert_called_once()
        orchestrator.plugins_manager.on_bot_stop.assert_called_once()
        orchestrator.log.log.assert_called_with("bye")
        mock_exit.assert_called_with(0)

    @patch("lendingbot.modules.Orchestrator.sys.exit")
    def test_orchestrator_handle_exception_critical(self, mock_sys_exit):
        """Test handling of critical exceptions that should exit."""
        orchestrator = BotOrchestrator(config_path="config.toml")
        orchestrator.log = MagicMock()
        orchestrator.engine = MagicMock()
        orchestrator.engine.sleep_time = 1
        orchestrator.config = MagicMock()

        # Test Invalid API key
        orchestrator._handle_exception(Exception("Invalid API key"))
        mock_sys_exit.assert_called_with(1)

    def test_orchestrator_handle_exception_recoverable(self):
        """Test handling of recoverable exceptions."""
        orchestrator = BotOrchestrator(config_path="config.toml")
        orchestrator.log = MagicMock()
        orchestrator.config = MagicMock()
        orchestrator.config.notifications.notify_caught_exception = False
        orchestrator.engine = MagicMock()
        orchestrator.engine.sleep_time = 1

        # Test generic exception
        orchestrator._handle_exception(Exception("Some random error"))
        # Should log error but not exit
        orchestrator.log.log_error.assert_called()
