"""
Tests for Charts plugin using Dependency Injection.
"""

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from lendingbot.modules.Configuration import PluginsConfig, RootConfig
from lendingbot.plugins.Charts import Charts


class TestCharts:
    @pytest.fixture
    def charts_plugin(self, tmp_path):
        # Use real configuration object
        mock_cfg = RootConfig(
            plugins=PluginsConfig(charts={"enabled": True, "DumpInterval": 21600})
        )
        mock_api = Mock()
        mock_log = MagicMock()

        with (
            patch("pathlib.Path.is_file", return_value=True),
            patch("sqlite3.connect") as mock_connect,
        ):
            db = sqlite3.connect(":memory:")
            db.execute("CREATE TABLE history(close TIMESTAMP, earned NUMBER, currency TEXT)")
            mock_connect.return_value = db

            plugin = Charts(mock_cfg, mock_api, mock_log, {})
            plugin.history_file = str(tmp_path / "history.json")
            plugin.on_bot_init()
            plugin.activeCurrencies = ["BTC"]
            yield plugin
            db.close()

    def test_on_bot_init(self, charts_plugin):
        assert charts_plugin.db is not None
        charts_plugin.log.addSectionLog.assert_called()

    def test_dump_history(self, charts_plugin):
        # Insert dummy data
        charts_plugin.db.execute(
            "INSERT INTO history (currency, earned, close) VALUES ('BTC', 0.1, '2025-12-30 00:00:00')"
        )
        charts_plugin.db.commit()

        mock_cursor = MagicMock()
        # Mocking the iterator behavior for the two queries in dump_history
        # 1. SELECT DISTINCT currency ...
        # 2. SELECT strftime ...
        mock_cursor.__iter__.side_effect = [iter([("BTC",)]), iter([(1735516800, 0.1)])]

        with patch.object(charts_plugin.db, "cursor", return_value=mock_cursor):
            charts_plugin.dump_history()

        # Verify file exists and content
        hist_path = Path(charts_plugin.history_file)
        assert hist_path.exists()
        with hist_path.open() as f:
            data = json.load(f)
            assert "BTC" in data
            assert len(data["BTC"]) == 1
            # [ts, earned, total]
            assert data["BTC"][0][1] == 0.1

    def test_after_lending_trigger(self, charts_plugin):
        with patch.object(charts_plugin, "dump_history") as mock_dump:
            # Set version > 0
            charts_plugin.db.execute("PRAGMA user_version = 1")
            charts_plugin.last_dump = 0
            charts_plugin.dump_interval = 0  # trigger immediately

            charts_plugin.after_lending()
            mock_dump.assert_called()
