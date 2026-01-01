"""
Tests for Lending module precedence logic.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from lendingbot.modules import Lending


def test_lending_init_precedence_web_settings():
    """
    Test that web settings take precedence over default.cfg.
    """
    # Mock Config to return "Default" values
    mock_config = MagicMock()
    # default.cfg says -10 and 10
    mock_config.get.side_effect = lambda sect, key, default=None, _min=None, _max=None: {
        ("BOT", "frrdelta_min"): -10,
        ("BOT", "frrdelta_max"): 10,
        ("BOT", "sleeptimeactive"): 60,
        ("BOT", "sleeptimeinactive"): 60,
        ("BOT", "mindailyrate"): 0.003,
        ("BOT", "maxdailyrate"): 0.003,
        ("BOT", "spreadlend"): 1,
        ("BOT", "gapbottom"): 0,
        ("BOT", "gaptop"): 0,
        ("BOT", "xdaythreshold"): "0.05:25",
        ("BOT", "minloansize"): 0.01,
        ("BOT", "keepstuckorders"): True,
        ("BOT", "hideCoins"): True,
        ("BOT", "frrasmin"): False,
        ("Daily_min", "method"): "percentile",
    }.get((sect, key), default)

    # Mock Config helpers
    mock_config.getboolean.return_value = False
    mock_config.get_exchange.return_value = "POLONIEX"
    mock_config.get_gap_mode.return_value = ""
    mock_config.get_coin_cfg.return_value = {}
    mock_config.get_min_loan_sizes.return_value = {}
    mock_config.get_currencies_list.return_value = []
    mock_config.get_all_currencies.return_value = []

    # Mock WebServer.get_web_settings to return "Web" values (-20, 20)
    web_settings = {"frrdelta_min": -20, "frrdelta_max": 20}

    with patch("lendingbot.modules.WebServer.get_web_settings", return_value=web_settings):
        Lending.init(
            mock_config,
            MagicMock(),  # api
            MagicMock(),  # log
            MagicMock(),  # data
            MagicMock(),  # maxtolend
            False,  # dry_run
            MagicMock(),  # analysis
            {"notify_summary_minutes": 0, "notify_new_loans": 0},  # notify_conf
        )

        # Verify Lending globals were updated to Web Settings
        assert Lending.frrdelta_min == Decimal("-20")
        assert Lending.frrdelta_max == Decimal("20")


def test_lending_init_precedence_no_web_settings():
    """
    Test that default.cfg is used when web settings do not overwrite.
    Note: In current implementation get_web_settings always returns defaults if missing.
    But if those defaults do not contain the keys (unlikely) or if we verify the init behavior
    when get_web_settings matches default.

    Actually, if get_web_settings returns defaults, it might NOT contain frrdelta_min/max if we removed them from defaults?
    No, DEFAULT_WEB_SETTINGS has them.

    So let's test if web settings returns 'empty' or missing keys.
    """
    mock_config = MagicMock()
    mock_config.get.side_effect = lambda sect, key, default=None, _min=None, _max=None: {
        ("BOT", "frrdelta_min"): -5,
        ("BOT", "frrdelta_max"): 5,
        ("BOT", "sleeptimeactive"): 60,
        ("BOT", "sleeptimeinactive"): 60,
        ("BOT", "mindailyrate"): 0.003,
        ("BOT", "maxdailyrate"): 0.003,
        ("BOT", "spreadlend"): 1,
        ("BOT", "gapbottom"): 0,
        ("BOT", "gaptop"): 0,
        ("BOT", "xdaythreshold"): "0.05:25",
        ("BOT", "minloansize"): 0.01,
        ("BOT", "keepstuckorders"): True,
        ("BOT", "hideCoins"): True,
        ("BOT", "frrasmin"): False,
        ("Daily_min", "method"): "percentile",
    }.get((sect, key), default)
    mock_config.get_all_currencies.return_value = []
    mock_config.get_currencies_list.return_value = []
    mock_config.get_coin_cfg.return_value = {}
    mock_config.get_min_loan_sizes.return_value = {}
    mock_config.get_gap_mode.return_value = ""
    mock_config.get_exchange.return_value = "POLONIEX"
    mock_config.getboolean.return_value = False

    # Empty web settings
    with patch("lendingbot.modules.WebServer.get_web_settings", return_value={}):
        Lending.init(
            mock_config,
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            False,
            MagicMock(),
            {"notify_summary_minutes": 0, "notify_new_loans": 0},
        )

        # Should stay as Config values
        assert Lending.frrdelta_min == Decimal("-5")
        assert Lending.frrdelta_max == Decimal("5")
