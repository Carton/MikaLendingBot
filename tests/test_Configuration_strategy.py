"""
Tests for Lending Strategy Selection in Configuration module
"""

import configparser
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
def mock_bitfinex_config(tmp_path):
    config_file = tmp_path / "bitfinex.cfg"
    content = """
[API]
exchange = Bitfinex

[BITFINEX]
all_currencies = BTC

[BTC]
mindailyrate = 0.01
maxactiveamount = 100
maxtolend = 1000
maxpercenttolend = 0.5
maxtolendrate = 0.05
gapmode = raw
gapbottom = 10
gaptop = 20
lending_strategy = FRR
frrdelta_min = 0.0001
frrdelta_max = 0.0005
"""
    config_file.write_text(content)
    return str(config_file)


@pytest.fixture
def mock_poloniex_config(tmp_path):
    config_file = tmp_path / "poloniex.cfg"
    content = """
[API]
exchange = Poloniex

[BTC]
mindailyrate = 0.01
maxactiveamount = 100
maxtolend = 1000
maxpercenttolend = 0.5
maxtolendrate = 0.05
gapmode = raw
gapbottom = 10
gaptop = 20
lending_strategy = Spread
"""
    config_file.write_text(content)
    return str(config_file)


def test_lending_strategy_default(tmp_path):
    """Test that lending_strategy defaults to Spread if missing"""
    config_file = tmp_path / "default.cfg"
    content = """
[API]
exchange = Poloniex
[BTC]
mindailyrate = 0.01
maxactiveamount = 100
maxtolend = 1000
maxpercenttolend = 0.5
maxtolendrate = 0.05
gapmode = raw
gapbottom = 10
gaptop = 20
"""
    config_file.write_text(content)
    Configuration.init(str(config_file))
    coin_cfg = Configuration.get_coin_cfg()
    assert coin_cfg["BTC"].lending_strategy == "Spread"


def test_lending_strategy_explicit_spread(mock_poloniex_config):
    """Test explicit Spread strategy"""
    Configuration.init(mock_poloniex_config)
    coin_cfg = Configuration.get_coin_cfg()
    assert coin_cfg["BTC"].lending_strategy == "Spread"


def test_lending_strategy_explicit_frr_bitfinex(mock_bitfinex_config):
    """Test explicit FRR strategy on Bitfinex"""
    Configuration.init(mock_bitfinex_config)
    coin_cfg = Configuration.get_coin_cfg()
    assert coin_cfg["BTC"].lending_strategy == "FRR"


def test_lending_strategy_frr_non_bitfinex(tmp_path):
    """Test that FRR strategy raises error on non-Bitfinex exchange"""
    config_file = tmp_path / "bad_strategy.cfg"
    content = """
[API]
exchange = Poloniex
[BTC]
mindailyrate = 0.01
maxactiveamount = 100
maxtolend = 1000
maxpercenttolend = 0.5
maxtolendrate = 0.05
gapmode = raw
gapbottom = 10
gaptop = 20
lending_strategy = FRR
"""
    config_file.write_text(content)
    Configuration.init(str(config_file))

    # Depending on implementation, this might raise SystemExit or specific Exception
    with patch("builtins.print"), pytest.raises(Exception) as cm:
        Configuration.get_coin_cfg()

    assert "FRR strategy is only supported on Bitfinex" in str(cm.value)


def test_lending_strategy_global_bot_config_validation(tmp_path):
    """
    Test that a global [BOT] lending_strategy=FRR is inherited and validated.
    It should raise an error if Exchange is not Bitfinex.
    """
    config_file = tmp_path / "global_strategy.cfg"
    content = """
[API]
exchange = Poloniex

[BOT]
lending_strategy = FRR

[BTC]
mindailyrate = 0.01
maxactiveamount = 100
maxtolend = 1000
maxpercenttolend = 0.5
maxtolendrate = 0.05
gapmode = raw
gapbottom = 10
gaptop = 20
"""
    config_file.write_text(content)
    Configuration.init(str(config_file))

    # This SHOULD raise an exception because [BOT] has FRR and Exchange is Poloniex
    with patch("builtins.print"), pytest.raises(Exception) as cm:
        Configuration.get_coin_cfg()

    assert "FRR strategy is only supported on Bitfinex" in str(cm.value)


def test_coin_config_fields():
    """Test that CoinConfig has lending_strategy and NO frrasmin"""
    from lendingbot.modules.Configuration import CoinConfig, LendingStrategy

    # Should succeed with lending_strategy
    cfg = CoinConfig(
        minrate=Decimal("0.01"),
        maxactive=Decimal("100"),
        maxtolend=Decimal("1000"),
        maxpercenttolend=Decimal("0.5"),
        maxtolendrate=Decimal("0.05"),
        gapmode="raw",
        gapbottom=Decimal("10"),
        gaptop=Decimal("20"),
        lending_strategy=LendingStrategy.SPREAD,
        frrdelta_min=Decimal("0.0001"),
        frrdelta_max=Decimal("0.0005"),
    )

    assert cfg.lending_strategy == LendingStrategy.SPREAD

    # accessing frrasmin should fail
    with pytest.raises(AttributeError):
        _ = cfg.frrasmin

    # instantiation with frrasmin should fail
    with pytest.raises(TypeError):
        CoinConfig(
            minrate=Decimal("0.01"),
            maxactive=Decimal("100"),
            maxtolend=Decimal("1000"),
            maxpercenttolend=Decimal("0.5"),
            maxtolendrate=Decimal("0.05"),
            gapmode="raw",
            gapbottom=Decimal("10"),
            gaptop=Decimal("20"),
            frrasmin=True,  # Old param
            frrdelta_min=Decimal("0.0001"),
            frrdelta_max=Decimal("0.0005"),
        )
