from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from lendingbot.modules.Configuration import CoinConfig, RootConfig

# This import will fail until we implement the class
from lendingbot.modules.Lending import LendingEngine


@pytest.fixture
def mock_config():
    """Create a minimal RootConfig for testing."""
    config = RootConfig()
    # Add some default coin config for testing
    config.coin = {"BTC": CoinConfig(min_daily_rate=Decimal("0.01")), "default": CoinConfig()}
    return config


@pytest.fixture
def mock_logger():
    return MagicMock()


@pytest.fixture
def mock_data():
    return MagicMock()


@pytest.fixture
def mock_api():
    return MagicMock()


@pytest.mark.unit
def test_lending_engine_initialize(mock_config, mock_data, mock_logger, mock_api):
    """Test that LendingEngine.initialize sets correct values from config."""
    engine = LendingEngine(mock_config, mock_api, mock_logger, mock_data)
    engine.initialize(dry_run=True)

    assert engine.dry_run is True
    # 'default' min_daily_rate is 0.005 (Pydantic default)
    assert engine.min_daily_rate == Decimal("0.005")
    # BTC min_daily_rate is 0.01 (Explicitly set in mock_config)
    assert engine.coin_cfg["BTC"].min_daily_rate == Decimal("0.01")
    assert engine.sleep_time == mock_config.bot.period_active


@pytest.mark.unit
def test_create_lend_offer(mock_config, mock_data, mock_logger, mock_api):
    """Test that create_lend_offer correctly calls the API."""
    engine = LendingEngine(mock_config, mock_api, mock_logger, mock_data)
    engine.initialize()

    engine.create_lend_offer("BTC", Decimal("0.1"), Decimal("0.01"), "2")

    # Verify API call
    mock_api.create_loan_offer.assert_called_once()
    args = mock_api.create_loan_offer.call_args[0]
    assert args[0] == "BTC"
    assert args[1] == 0.1
    assert args[2] == 2
    # rate is adjusted by -0.000001 if > 0.0001
    assert float(args[4]) == pytest.approx(0.009999)


@pytest.mark.unit
def test_get_min_daily_rate_default(mock_config, mock_api, mock_logger, mock_data):
    """Test get_min_daily_rate with default value."""
    engine = LendingEngine(mock_config, mock_api, mock_logger, mock_data)
    engine.initialize()

    # default in mock_config is 0.005
    rate = engine.get_min_daily_rate("USDT")
    assert rate == Decimal("0.005")


@pytest.mark.unit
def test_get_min_daily_rate_btc(mock_config, mock_api, mock_logger, mock_data):
    """Test get_min_daily_rate with coin-specific value."""
    engine = LendingEngine(mock_config, mock_api, mock_logger, mock_data)
    engine.initialize()

    # BTC in mock_config is 0.01
    rate = engine.get_min_daily_rate("BTC")
    assert rate == Decimal("0.01")


@pytest.mark.unit
def test_get_cur_spread(mock_config, mock_api, mock_logger, mock_data):
    """Test get_cur_spread logic."""
    engine = LendingEngine(mock_config, mock_api, mock_logger, mock_data)
    engine.initialize()
    engine.spread_lend = 3
    engine.min_loan_size = Decimal("0.01")

    # balance 0.05, can spread 3 times
    assert engine.get_cur_spread(3, Decimal("0.05"), "BTC") == 3
    # balance 0.015, can only spread 1 time
    assert engine.get_cur_spread(3, Decimal("0.015"), "BTC") == 1


@pytest.mark.unit
def test_get_gap_rate(mock_config, mock_api, mock_logger, mock_data):
    """Test get_gap_rate depth calculation."""
    engine = LendingEngine(mock_config, mock_api, mock_logger, mock_data)
    engine.initialize()
    engine.loan_orders_request_limit["BTC"] = 5
    engine.max_daily_rate = Decimal("0.1")

    order_book = {"rates": [0.01, 0.02, 0.03, 0.04, 0.05], "volumes": [10, 10, 10, 10, 10]}

    # Gap 15 at total balance 100 -> gap_expected = 15
    # sum of volumes: 10 (index 0) < 15, 20 (index 1) >= 15.
    # Original logic returns rates[i] AFTER increment, so it returns rates[2] = 0.03
    rate = engine.get_gap_rate("BTC", Decimal("15"), order_book, Decimal("100"))
    assert rate == Decimal("0.03")

    # Gap raw 25
    # i=0, sum=10, i=1. 10 < 25
    # i=1, sum=20, i=2. 20 < 25
    # i=2, sum=30, i=3. 30 >= 25. Loop ends.
    # Returns rates[3] = 0.04
    rate = engine.get_gap_rate("BTC", Decimal("25"), order_book, Decimal("100"), raw=True)
    assert rate == Decimal("0.04")
