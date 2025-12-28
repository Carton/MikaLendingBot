"""
Tests for Logger class
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

from lendingbot.modules.Logger import ConsoleOutput, JsonOutput, Logger


def test_console_output_status() -> None:
    """Test ConsoleOutput status update (manual verification of stderr is hard, so we just check it runs)"""
    co = ConsoleOutput()
    co.status("Testing Status")
    assert co._status == "Testing Status"


def test_json_output_printline(tmp_path: Any) -> None:
    """Test JsonOutput printline and writeJsonFile"""
    log_file = tmp_path / "test.json"
    with patch("lendingbot.modules.Configuration.get", return_value="Test Bot"):
        jo = JsonOutput(str(log_file), 5, "TestExchange")

    jo.printline("Test Line 1")
    jo.status("Running", "2025-12-28 12:00:00", " (3 Days Remaining)")
    jo.writeJsonFile()

    assert log_file.exists()
    with Path(log_file).open(encoding="utf-8") as f:
        data = json.load(f)
        assert data["exchange"] == "TestExchange"
        assert data["last_status"] == "Running"
        assert "Test Line 1" in data["log"][0]


def test_logger_log() -> None:
    """Test Logger log method"""
    with patch("lendingbot.modules.Logger.ConsoleOutput") as mock_output:
        logger = Logger()
        logger.log("Hello World")
        mock_output.return_value.printline.assert_called()


def test_logger_timestamp() -> None:
    """Test Logger timestamp format"""
    ts = Logger.timestamp()
    assert len(ts) == 19  # YYYY-MM-DD HH:MM:SS
    assert ts[4] == "-"
    assert ts[13] == ":"


def test_logger_digest_api_msg() -> None:
    """Test Logger.digestApiMsg"""
    assert Logger.digestApiMsg({"message": "Success"}) == "Success"
    assert Logger.digestApiMsg({"error": "Failed"}) == "Failed"
    assert Logger.digestApiMsg("Something else") == "Something else"
    assert Logger.digestApiMsg({}) == ""
