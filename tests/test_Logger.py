"""
Tests for Logger module.
"""

import json
import os

from unittest.mock import patch

from lendingbot.modules.Logger import ConsoleOutput, JsonOutput, Logger


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

    def test_json_output(self, tmp_path):
        json_file = tmp_path / "botlog.json"
        out = JsonOutput(str(json_file), 10, "POLONIEX")

        out.status("Status", "2025-12-30", " - 1 Day")
        out.printline("Log Line 1")
        out.statusValue("BTC", "lentSum", "1.0")

        out.writeJsonFile()

        assert json_file.exists()
        with json_file.open() as f:
            data = json.load(f)
            assert data["exchange"] == "POLONIEX"
            assert data["last_status"] == "Status"
            assert "Log Line 1" in data["log"]
            assert data["raw_data"]["BTC"]["lentSum"] == "1.0"

    def test_logger_lifecycle(self, tmp_path):
        json_file = tmp_path / "botlog.json"
        logger = Logger(str(json_file), 5, "BITFINEX")

        logger.log("Info Message")
        logger.log_error("Error Message")
        logger.offer(1.0, "BTC", 0.01, "2", "Offer Message")
        logger.cancelOrder("BTC", "Cancel Message")

        logger.updateStatusValue("BTC", "test", "val")
        logger.persistStatus()

        assert json_file.exists()

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
