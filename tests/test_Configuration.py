"""
Tests for Configuration module
"""

import configparser
import os
import re
from decimal import Decimal
from unittest.mock import patch

import pytest

from lendingbot.modules import Configuration


@pytest.fixture(autouse=True)
def reset_config():
    """Reset the global state of the Configuration module before each test."""
    Configuration.config = configparser.ConfigParser()
    Configuration.Data = None


@pytest.fixture
def mock_config_file(tmp_path):
    config_file = tmp_path / "test.cfg"
    content = """
[BOT]
label = Test Bot
plugins = AccountStats,Charts
mindailyrate = 0.01
maxactiveamount = 100
maxtolend = 1000
maxpercenttolend = 0.5
maxtolendrate = 0.05
gapmode = raw
gapbottom = 10
gaptop = 20
frrasmin = True
frrdelta_min = 0.0001
frrdelta_max = 0.0005
test_all = ALL
test_active = ACTIVE

[API]
exchange = Bitfinex

[BITFINEX]
all_currencies = BTC,ETH,LTC

[BTC]
mindailyrate = 0.02
maxactiveamount = 50
maxtolend = 500
maxpercenttolend = 0.25
maxtolendrate = 0.025
gapmode = rawbtc
gapbottom = 5
gaptop = 15
minloansize = 0.01

[notifications]
notify_summary_minutes = 60
"""
    config_file.write_text(content)
    return str(config_file)


def test_init_and_get(mock_config_file):
    """Test initializing and getting values from config"""
    Configuration.init(mock_config_file)
    assert Configuration.get("BOT", "label") == "Test Bot"
    assert Configuration.get("API", "exchange") == "Bitfinex"


def test_init_file_not_found(tmp_path):
    """Test init when config file is not found"""
    missing_file = str(tmp_path / "missing.cfg")
    # Mock shutil.copy to prevent actually copying files
    # Mock sys.exit to prevent the test from exiting
    # Mock input to prevent hanging
    with (
        patch("shutil.copy") as mock_copy,
        patch("builtins.print"),
        patch("builtins.input", return_value=""),
        pytest.raises(SystemExit) as cm,
    ):
        Configuration.init(missing_file)
    assert cm.value.code == 1
    mock_copy.assert_called_once_with("default.cfg.example", missing_file)


def test_init_file_copy_fail(tmp_path):
    """Test init when config file copy fails"""
    missing_file = str(tmp_path / "missing.cfg")
    with (
        patch("shutil.copy", side_effect=Exception("Copy failed")),
        patch("builtins.print") as mock_print,
        pytest.raises(SystemExit) as cm,
    ):
        Configuration.init(missing_file)
    assert cm.value.code == 1
    # Check if error message was printed
    any_copy_fail_msg = any(
        "Failed to automatically copy" in str(call) for call in mock_print.call_args_list
    )
    assert any_copy_fail_msg


def test_init_with_deprecated_coinconfig(tmp_path):
    """Test init with deprecated coinconfig option"""
    config_file = tmp_path / "deprecated.cfg"
    config_file.write_text("[BOT]\ncoinconfig = something\n")
    with patch("builtins.print"), pytest.raises(SystemExit) as cm:
        Configuration.init(str(config_file))
    assert cm.value.code == 1


def test_getboolean(mock_config_file):
    """Test getboolean with env vars and config file"""
    Configuration.init(mock_config_file)
    assert Configuration.getboolean("BOT", "frrasmin") is True

    with patch.dict(os.environ, {"BOT_frrasmin": "False"}):
        assert Configuration.getboolean("BOT", "frrasmin") is False

    for val in ["true", "1", "t", "y", "yes"]:
        with patch.dict(os.environ, {"BOT_test": val}):
            assert Configuration.getboolean("BOT", "test", default_value=False) is True

    assert Configuration.getboolean("NON_EXISTENT", "option", default_value=True) is True


def test_get_with_limits(mock_config_file):
    """Test get with lower and upper limits"""
    Configuration.init(mock_config_file)
    assert Configuration.get("BOT", "mindailyrate") == "0.01"

    # Test lower limit
    with patch("builtins.print") as mock_print:
        assert Configuration.get("BOT", "mindailyrate", lower_limit=0.05) == "0.05"
        assert any("is below the minimum limit" in str(call) for call in mock_print.call_args_list)

    # Test upper limit
    with patch("builtins.print") as mock_print:
        assert Configuration.get("BOT", "mindailyrate", upper_limit=0.005) == "0.005"
        assert any("is above the maximum limit" in str(call) for call in mock_print.call_args_list)


def test_get_missing_value_exit(mock_config_file):
    """Test get with missing value and default_value=None exit"""
    Configuration.init(mock_config_file)
    with patch("builtins.print"), pytest.raises(SystemExit) as cm:
        Configuration.get("BOT", "non_existent_option", default_value=None)
    assert cm.value.code == 1


def test_get_value_error_exit(mock_config_file):
    """Test get with ValueError and default_value=None exit"""
    Configuration.init(mock_config_file)
    # We use mindailyrate which has limits in the get call later,
    # so it will trigger float() conversion
    with (
        patch.dict(os.environ, {"BOT_mindailyrate": "not_a_number"}),
        patch("builtins.print"),
        pytest.raises(SystemExit) as cm,
    ):
        # lower_limit=0 forces float conversion
        Configuration.get("BOT", "mindailyrate", default_value=None, lower_limit=0)
    assert cm.value.code == 1


def test_get_value_error_default(mock_config_file):
    """Test get with ValueError returns default when provided"""
    Configuration.init(mock_config_file)
    with patch.dict(os.environ, {"BOT_mindailyrate": "not_a_number"}):
        assert Configuration.get("BOT", "mindailyrate", default_value="0.1", lower_limit=0) == "0.1"


def test_get_exchange(mock_config_file):
    """Test get_exchange with env var and config"""
    Configuration.init(mock_config_file)
    assert Configuration.get_exchange() == "BITFINEX"

    with patch.dict(os.environ, {"API_EXCHANGE": "POLONIEX"}):
        assert Configuration.get_exchange() == "POLONIEX"

    # Test exception in get_exchange
    with patch("lendingbot.modules.Configuration.get", side_effect=Exception("Error")):
        assert Configuration.get_exchange() == "POLONIEX"


def test_get_all_currencies(mock_config_file):
    """Test get_all_currencies"""
    Configuration.init(mock_config_file)
    currencies = Configuration.get_all_currencies()
    assert "BTC" in currencies
    assert "ETH" in currencies
    assert "LTC" in currencies


def test_get_all_currencies_poloniex(tmp_path):
    """Test get_all_currencies for Poloniex defaults"""
    config_file = tmp_path / "poloniex.cfg"
    config_file.write_text("[API]\nexchange = Poloniex\n")
    Configuration.init(str(config_file))
    currencies = Configuration.get_all_currencies()
    assert "BTC" in currencies
    assert "ETH" in currencies


def test_get_all_currencies_unknown(tmp_path):
    """Test get_all_currencies for unknown exchange"""
    config_file = tmp_path / "unknown.cfg"
    config_file.write_text("[API]\nexchange = Unknown\n")
    Configuration.init(str(config_file))
    with pytest.raises(Exception, match=re.escape("List of supported currencies must defined")):
        Configuration.get_all_currencies()


def test_get_all_currencies_blacklist(tmp_path):
    """Test get_all_currencies with blacklisting"""
    config_file = tmp_path / "blacklist.cfg"
    config_file.write_text("[API]\nexchange = MOCK\n[MOCK]\nall_currencies = BTC, #BTG, ETH\n")
    Configuration.init(str(config_file))
    currencies = Configuration.get_all_currencies()
    assert "BTC" in currencies
    assert "ETH" in currencies
    assert "BTG" not in currencies


def test_get_currencies_list(mock_config_file):
    """Test get_currencies_list"""
    Configuration.init(mock_config_file)
    currencies = Configuration.get_currencies_list("all_currencies", section="BITFINEX")
    assert "BTC" in currencies
    assert "ETH" in currencies
    assert "LTC" in currencies

    # Test ALL
    currencies = Configuration.get_currencies_list("test_all")
    assert "BTC" in currencies
    assert "ETH" in currencies

    # Test ACTIVE
    class MockData:
        def get_lending_currencies(self):
            return ["BTC", "XRP"]

    Configuration.Data = MockData()
    currencies = Configuration.get_currencies_list("test_active")
    assert "BTC" in currencies
    assert "XRP" in currencies


def test_get_coin_cfg(mock_config_file):
    """Test get_coin_cfg"""
    Configuration.init(mock_config_file)
    coin_cfg = Configuration.get_coin_cfg()
    assert "BTC" in coin_cfg
    assert coin_cfg["BTC"].minrate == Decimal("0.0002")  # 0.02 / 100

    # Test missing section (should just skip)
    with patch(
        "lendingbot.modules.Configuration.get_all_currencies", return_value=["NON_EXISTENT"]
    ):
        assert Configuration.get_coin_cfg() == {}

    # Test parsing error
    with (
        patch.object(Configuration.config, "get", side_effect=Exception("Parsing error")),
        patch("builtins.print"),
        pytest.raises(Exception, match="Parsing error"),
    ):
        Configuration.get_coin_cfg()


def test_get_min_loan_sizes(mock_config_file):
    """Test get_min_loan_sizes"""
    Configuration.init(mock_config_file)
    min_loan_sizes = Configuration.get_min_loan_sizes()
    assert min_loan_sizes["BTC"] == Decimal("0.01")

    # Test parsing error
    with (
        patch("lendingbot.modules.Configuration.get_all_currencies", return_value=["BTC"]),
        patch(
            "lendingbot.modules.Configuration.get",
            side_effect=Exception("Parsing error"),
        ),
        patch("builtins.print"),
        pytest.raises(Exception, match="Parsing error"),
    ):
        Configuration.get_min_loan_sizes()


def test_get_gap_mode(mock_config_file):
    """Test get_gap_mode"""
    Configuration.init(mock_config_file)
    assert Configuration.get_gap_mode("BOT", "gapmode") == "raw"
    assert Configuration.get_gap_mode("BTC", "gapmode") == "rawbtc"
    assert Configuration.get_gap_mode("NON_EXISTENT", "gapmode") is False

    # Invalid mode should exit
    with (
        patch.dict(os.environ, {"BOT_gapmode": "invalid"}),
        patch("builtins.print"),
        pytest.raises(SystemExit) as cm,
    ):
        Configuration.get_gap_mode("BOT", "gapmode")
    assert cm.value.code == 1

    # False raw_val
    with patch("lendingbot.modules.Configuration.get", return_value=False):
        assert Configuration.get_gap_mode("BOT", "gapmode") is False


def test_get_notification_config_all(tmp_path):
    """Test get_notification_config with various providers"""
    config_file = tmp_path / "notify.cfg"
    content = """
[notifications]
email = True
slack = True
telegram = True
pushbullet = True
irc = True
notify_summary_minutes = 30
notify_prefix = BOT:
email_login_address = user@example.com
email_login_password = pass
email_smtp_server = smtp.example.com
email_smtp_port = 587
email_to_addresses = a@bc.com,b@bc.com
email_smtp_starttls = True
slack_token = xxxx
slack_channels = #general,#bot
slack_username = MyBot
telegram_bot_id = 1234
telegram_chat_ids = 5678,9012
pushbullet_token = pbbb
pushbullet_deviceid = dev1
irc_host = irc.freenode.net
irc_port = 6667
irc_nick = lbot
irc_ident = lbot
irc_realname = Lending Bot
irc_target = #lendingbot
irc_debug = True
"""
    config_file.write_text(content)
    Configuration.init(str(config_file))
    notify_conf = Configuration.get_notification_config()

    assert notify_conf["email"] is True
    assert notify_conf["slack_channels"] == ["#general", "#bot"]
    assert notify_conf["telegram_chat_ids"] == ["5678", "9012"]
    assert notify_conf["irc_port"] == 6667
    assert notify_conf["notify_summary_minutes"] == 30
    assert notify_conf["notify_prefix"] == "BOT:"


def test_get_notification_config_summary_false(tmp_path):
    """Test get_notification_config with notify_summary_minutes = False"""
    config_file = tmp_path / "notify_false.cfg"
    config_file.write_text("[notifications]\nnotify_summary_minutes = False\n")
    Configuration.init(str(config_file))
    notify_conf = Configuration.get_notification_config()
    assert notify_conf["notify_summary_minutes"] == 0


def test_get_plugins_config(mock_config_file):
    """Test get_plugins_config"""
    Configuration.init(mock_config_file)
    plugins = Configuration.get_plugins_config()
    assert "AccountStats" in plugins
    assert "Charts" in plugins

    # Test empty plugins
    Configuration.config.remove_option("BOT", "plugins")
    assert Configuration.get_plugins_config() == []

    # Test missing plugins option
    Configuration.config.remove_section("BOT")
    Configuration.config.add_section("BOT")
    assert Configuration.get_plugins_config() == []
