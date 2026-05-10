"""
Tests for Logger module.
"""

import json
import os
from unittest.mock import patch

from lendingbot.modules.Logger import ConsoleOutput, Logger, StatsOutput


class TestLogger:
    def test_console_output(self):
        with (
            patch("sys.stderr.write") as mock_write,
            patch("shutil.get_terminal_size", return_value=os.terminal_size((80, 25))),
        ):
            out = ConsoleOutput()
            out.status("Test Status")
            mock_write.assert_called()

            out.printline("Test Line")
            mock_write.assert_called()

    def test_stats_output(self, tmp_path):
        stats_file = tmp_path / "bot_stats.json"
        out = StatsOutput(str(stats_file), 10, "POLONIEX")

        out.status("Status", "2025-12-30", " - 1 Day")
        out.printline("Log Line 1")
        out.statusValue("BTC", "lentSum", "1.0")

        out.writeStatsFile()

        assert stats_file.exists()
        with stats_file.open() as f:
            data = json.load(f)
            assert data["exchange"] == "POLONIEX"
            assert data["last_status"] == "Status"
            assert "log" not in data
            assert data["raw_data"]["BTC"]["lentSum"] == "1.0"

        # Test get_recent_logs
        assert "Log Line 1" in out.get_recent_logs()

    def test_stats_snapshot_is_copy(self, tmp_path):
        stats_file = tmp_path / "bot_stats.json"
        logger = Logger(str(stats_file), 5, "BITFINEX")
        logger.updateStatusValue("BTC", "lentSum", "1.0")

        snapshot = logger.get_stats_snapshot()
        snapshot["raw_data"]["BTC"]["lentSum"] = "2.0"

        assert logger.get_stats_snapshot()["raw_data"]["BTC"]["lentSum"] == "1.0"

    def test_write_status_snapshot_does_not_clear_values(self, tmp_path):
        stats_file = tmp_path / "bot_stats.json"
        logger = Logger(str(stats_file), 5, "BITFINEX")
        logger.updateStatusValue("BTC", "lentSum", "1.0")

        logger.writeStatusSnapshot()

        with stats_file.open() as f:
            data = json.load(f)
        assert data["raw_data"]["BTC"]["lentSum"] == "1.0"
        assert logger.get_stats_snapshot()["raw_data"]["BTC"]["lentSum"] == "1.0"

    def test_logger_lifecycle(self, tmp_path):
        stats_file = tmp_path / "bot_stats.json"
        logger = Logger(str(stats_file), 5, "BITFINEX")

        logger.log("Info Message")
        logger.log_error("Error Message")
        logger.offer(1.0, "BTC", 0.01, "2", "Offer Message")
        logger.cancelOrder("BTC", "Cancel Message")

        logger.updateStatusValue("BTC", "test", "val")
        logger.persistStatus()

        assert stats_file.exists()

    def test_digest_api_msg(self):
        assert Logger.digestApiMsg({"message": "success"}) == "success"
        assert Logger.digestApiMsg({"error": "fail"}) == "fail"
        assert Logger.digestApiMsg("raw string") == "raw string"
        assert Logger.digestApiMsg(None) == ""

    def test_notify(self):
        with patch("lendingbot.modules.Logger.send_notification") as mock_send:
            conf = {"enable_notifications": True}
            Logger.notify("Msg", conf)
            mock_send.assert_called_with("Msg", conf)

            conf = {"enable_notifications": False}
            Logger.notify("Msg", conf)
            # Should not call if disabled
            assert mock_send.call_count == 1
