"""
Tests for AccountStats plugin.
"""

import sqlite3
from unittest.mock import MagicMock, Mock, patch

import pytest

from lendingbot.plugins.AccountStats import AccountStats


class TestAccountStats:
    @pytest.fixture
    def account_stats(self):
        mock_cfg = Mock()
        mock_cfg.get.side_effect = lambda _s, _k, d=None: d
        mock_api = Mock()
        mock_api.create_time_stamp.side_effect = lambda _x: 1000.0  # simple mock
        mock_log = MagicMock()

        # Create a real in-memory database for testing
        db = sqlite3.connect(":memory:")

        with (
            patch("sqlite3.connect", return_value=db),
            patch("time.sleep"),
        ):  # Prevent any accidental hangs
            stats = AccountStats(mock_cfg, mock_api, mock_log, {})
            stats.init_db()
            yield stats
            db.close()

    def test_init_and_upgrade(self, account_stats):
        # Initial version should be 0
        assert account_stats.get_db_version() == 0

        # Test upgrade path
        account_stats.set_db_version(1)
        account_stats.check_upgrade()
        # The code sets version to 0 during upgrade to reinitialize
        assert account_stats.get_db_version() == 0
        account_stats.log.log.assert_called_with("Upgraded AccountStats DB to version 2")

    def test_fetch_history(self, account_stats):
        account_stats.api.return_lending_history.return_value = [
            {
                "id": 1,
                "open": "2025-12-30 00:00:00",
                "close": "2025-12-30 01:00:00",
                "duration": 0.04,
                "interest": "0.0001",
                "rate": "0.01",
                "currency": "BTC",
                "amount": "1.0",
                "earned": "0.000085",
                "fee": "0.000015",
            }
        ]

        count = account_stats.fetch_history(1000, 2000)
        assert count == 1

        res = account_stats.db.execute("SELECT count(*) FROM history").fetchone()
        assert res[0] == 1

    def test_notify_stats(self, account_stats):
        # Insert dummy data
        account_stats.db.execute(
            "INSERT INTO history (id, currency, earned, close) VALUES (1, 'BTC', 0.5, datetime('now'))"
        )
        account_stats.db.execute(
            "INSERT INTO history (id, currency, earned, close) VALUES (2, 'BTC', 0.3, datetime('now', '-1 day'))"
        )
        account_stats.db.commit()

        # Mock version to > 0
        account_stats.set_db_version(2)

        account_stats.notify_stats()
        account_stats.log.notify.assert_called()
        assert "BTC" in account_stats.earnings
        assert float(account_stats.earnings["BTC"]["todayEarnings"]) == 0.5
        assert float(account_stats.earnings["BTC"]["yesterdayEarnings"]) == 0.3

    def test_update_history_empty(self, account_stats):
        # Test update_history when DB is empty
        with patch.object(account_stats, "fetch_history", return_value=0) as mock_fetch:
            account_stats.update_history()
            mock_fetch.assert_called()
