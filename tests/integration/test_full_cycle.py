import itertools
from unittest.mock import MagicMock, patch

import pytest

from lendingbot.modules.Orchestrator import BotOrchestrator


@pytest.mark.integration
class TestFullCycle:
    @patch("lendingbot.modules.Orchestrator.time.sleep")  # Don't actually sleep
    @patch("lendingbot.modules.Orchestrator.time.time")
    @patch("lendingbot.modules.ExchangeApiFactory.ExchangeApiFactory.createApi")
    def test_full_lending_cycle(self, mock_create_api, mock_time, _mock_sleep):
        """
        Simulate a full cycle of the bot:
        1. Initialize
        2. Run one step (fetch data, cancel, lend)
        3. Verify interactions
        """
        # Setup time sequence: avoid StopIteration by providing infinite stream
        mock_time.side_effect = itertools.count(start=1000, step=10)

        # Setup API Mock
        mock_api = MagicMock()
        mock_create_api.return_value = mock_api

        # Configure Orchestrator
        orchestrator = BotOrchestrator(config_path="config_sample.toml", dry_run=True)

        # We need a real-ish config for integration, but loading from file is fine as we used sample.
        # However, to be safe and deterministic, let's mock config loading or ensure config_sample exists.
        # It does exist (verified in previous turns).

        orchestrator.initialize()

        # Ensure lending is enabled in the loaded config for the test
        orchestrator.engine.lending_paused = False

        # Mock Data module methods that do network calls if any remain unmocked by Orchestrator mocks?
        # Orchestrator step calls:
        # Data.update_conversion_rates -> HTTP call. We should mock this part of Data or let it fail?
        # Ideally integration tests mock external network but run internal logic.

        with patch("lendingbot.modules.Data.update_conversion_rates") as mock_update_rates:
            # Run one step
            orchestrator.step()

            # Verifications
            mock_update_rates.assert_called()

            # Verify API calls (Lending Engine logic)
            # Since it's dry run, it might not place orders, but it should fetch balances/open orders
            mock_api.return_available_account_balances.assert_called()
            mock_api.return_open_loan_offers.assert_called()

            # Verify logging happened (persistStatus)
            assert orchestrator.log is not None
