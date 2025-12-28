"""
Tests for Configuration module
"""

import os
from unittest.mock import patch

import pytest

from lendingbot.modules import Configuration


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
"""
    config_file.write_text(content)
    return str(config_file)


def test_init_and_get(mock_config_file):
    """Test initializing and getting values from config"""
    Configuration.init(mock_config_file)
    assert Configuration.get("BOT", "label") == "Test Bot"
    assert Configuration.get("API", "exchange") == "Bitfinex"


def test_getboolean(mock_config_file):
    """Test getboolean with env vars and config file"""
    Configuration.init(mock_config_file)
    assert Configuration.getboolean("BOT", "frrasmin") is True

    with patch.dict(os.environ, {"BOT_frrasmin": "False"}):
        assert Configuration.getboolean("BOT", "frrasmin") is False


def test_get_with_limits(mock_config_file):
    """Test get with lower and upper limits"""
    Configuration.init(mock_config_file)
    assert Configuration.get("BOT", "mindailyrate") == "0.01"

    # Test lower limit
    assert Configuration.get("BOT", "mindailyrate", lower_limit=0.05) == "0.05"

    # Test upper limit
    assert Configuration.get("BOT", "mindailyrate", upper_limit=0.005) == "0.005"


def test_get_exchange(mock_config_file):
    """Test get_exchange with env var and config"""
    Configuration.init(mock_config_file)
    assert Configuration.get_exchange() == "BITFINEX"

    with patch.dict(os.environ, {"API_EXCHANGE": "POLONIEX"}):
        assert Configuration.get_exchange() == "POLONIEX"


def test_get_all_currencies(mock_config_file):
    """Test get_all_currencies"""
    Configuration.init(mock_config_file)
    currencies = Configuration.get_all_currencies()
    assert "BTC" in currencies
    assert "ETH" in currencies
    assert "LTC" in currencies


def test_get_currencies_list(mock_config_file):
    """Test get_currencies_list"""
    Configuration.init(mock_config_file)
    currencies = Configuration.get_currencies_list("all_currencies", section="BITFINEX")
    assert "BTC" in currencies
    assert "ETH" in currencies
    assert "LTC" in currencies


def test_get_coin_cfg(mock_config_file):
    """Test get_coin_cfg"""
    Configuration.init(mock_config_file)
    coin_cfg = Configuration.get_coin_cfg()
    assert "BTC" in coin_cfg
    assert coin_cfg["BTC"]["minrate"] == Configuration.Decimal("0.0002")  # 0.02 / 100
