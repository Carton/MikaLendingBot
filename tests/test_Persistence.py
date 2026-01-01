import json
from unittest.mock import MagicMock, patch

import pytest

from lendingbot.modules import Lending, WebServer


@pytest.fixture
def mock_cfg():
    cfg = MagicMock()
    cfg.get_exchange.return_value = "BITFINEX"

    def get_side_effect(section, key, *args, **kwargs):
        if key == "spreadlend":
            return "1"
        if key in ["sleeptimeactive", "sleeptimeinactive"]:
            return "60"
        return "0.01"

    cfg.get.side_effect = get_side_effect
    cfg.get_gap_mode.return_value = False
    cfg.get_coin_cfg.return_value = {}
    cfg.get_min_loan_sizes.return_value = {}
    cfg.get_currencies_list.return_value = []
    cfg.get_all_currencies.return_value = []
    cfg.getboolean.return_value = False
    return cfg


def test_lending_paused_persistence_load(mock_cfg):
    """Verify Lending.init correctly loads the paused state from mocked WebServer settings."""

    # Reset globals to ensure clean state
    Lending._reset_globals()
    mock_log = MagicMock()

    # Patch WebServer.get_web_settings to return our desired state
    with patch("lendingbot.modules.WebServer.get_web_settings") as mock_get_settings:
        mock_get_settings.return_value = {
            "lending_paused": True,
            "frrdelta_min": -10,
            "frrdelta_max": 10,
        }

        Lending.init(
            cfg=mock_cfg,
            api1=MagicMock(),
            log1=mock_log,
            data=MagicMock(),
            maxtolend=MagicMock(),
            dry_run1=False,
            analysis=MagicMock(),
            notify_conf1={"notify_summary_minutes": 0, "notify_new_loans": False},
        )

        # Verify mock was called
        mock_get_settings.assert_called()

    # Verify lending_paused is True
    assert Lending.lending_paused is True
    # Verify we logged it
    mock_log.log.assert_any_call("Loaded lending_paused=True from Web Configuration.")


def test_lending_paused_persistence_default(mock_cfg):
    """Verify defaults are used when settings do not have the key."""

    Lending._reset_globals()
    mock_log = MagicMock()

    with patch("lendingbot.modules.WebServer.get_web_settings") as mock_get_settings:
        # Return empty settings or settings without the key
        mock_get_settings.return_value = {}

        Lending.init(
            cfg=mock_cfg,
            api1=MagicMock(),
            log1=mock_log,
            data=MagicMock(),
            maxtolend=MagicMock(),
            dry_run1=False,
            analysis=MagicMock(),
            notify_conf1={"notify_summary_minutes": 0, "notify_new_loans": False},
        )

    assert Lending.lending_paused is False


def test_web_endpoint_saves_state(tmp_path):
    """Verify save_web_settings writes correctly to file."""
    # We test the save_web_settings function directly since do_GET calls it.

    test_file = tmp_path / "web_settings_test.json"

    # Patch the filename in WebServer to use our temp file
    with patch("lendingbot.modules.WebServer.web_settings_file", str(test_file)):
        # 1. Save True
        WebServer.save_web_settings({"lending_paused": True})
        with test_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["lending_paused"] is True

        # 2. Save False (partial update check - ensure it updates existing)
        WebServer.save_web_settings({"lending_paused": False})
        with test_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["lending_paused"] is False

        # 3. Check that other keys are preserved if we merge (implementation specific)
        # The implementation uses update(), so let's verify.
        WebServer.save_web_settings({"other_key": 123})
        with test_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["lending_paused"] is False
        assert data["other_key"] == 123
