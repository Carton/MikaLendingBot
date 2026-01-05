"""
Tests for Persistence logic using Dependency Injection.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from lendingbot.modules.Configuration import RootConfig
from lendingbot.modules.Lending import LendingEngine
from lendingbot.modules.WebServer import WebServer


@pytest.fixture
def mock_config():
    return RootConfig()


@pytest.fixture
def mock_api():
    return MagicMock()


@pytest.fixture
def mock_log():
    return MagicMock()


@pytest.fixture
def mock_data():
    return MagicMock()


class TestPersistence:
    def test_lending_paused_persistence_load(self, mock_config, mock_api, mock_log, mock_data):
        """Verify LendingEngine initializes correctly loads the paused state from mocked WebServer settings."""

        # We need to patch the MODULE level WebServer.get_web_settings function
        # because LendingEngine uses the backward compatible wrapper.
        with patch("lendingbot.modules.WebServer.get_web_settings") as mock_get_settings:
            mock_get_settings.return_value = {
                "lending_paused": True,
                "frrdelta_min": -10,
                "frrdelta_max": 10,
            }

            engine = LendingEngine(mock_config, mock_api, mock_log, mock_data)
            engine.initialize()

            # Verify mock was called
            mock_get_settings.assert_called()

            # Verify lending_paused is True
            assert engine.lending_paused is True
            # Verify we logged it
            mock_log.log.assert_any_call("Loaded lending_paused=True from Web Configuration.")

    def test_lending_paused_persistence_default(self, mock_config, mock_api, mock_log, mock_data):
        """Verify defaults are used when settings do not have the key."""

        with patch("lendingbot.modules.WebServer.get_web_settings") as mock_get_settings:
            # Return empty settings or settings without the key
            mock_get_settings.return_value = {}

            engine = LendingEngine(mock_config, mock_api, mock_log, mock_data)
            engine.initialize()

            assert engine.lending_paused is False

    def test_web_endpoint_saves_state(self, mock_config, tmp_path):
        """Verify WebServer.save_web_settings writes correctly to file."""

        mock_engine = MagicMock()
        web_server = WebServer(mock_config, mock_engine)

        test_file = tmp_path / "web_settings_test.json"
        web_server.web_settings_file = str(test_file)

        # 1. Save True
        web_server.save_web_settings({"lending_paused": True})
        with test_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["lending_paused"] is True

        # 2. Save False (partial update check - ensure it updates existing)
        web_server.save_web_settings({"lending_paused": False})
        with test_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["lending_paused"] is False

        # 3. Check that other keys are preserved if we merge
        web_server.save_web_settings({"other_key": 123})
        with test_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["lending_paused"] is False
        assert data["other_key"] == 123
