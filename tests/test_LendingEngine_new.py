import pytest
from unittest.mock import MagicMock
from decimal import Decimal

# This import will fail until we implement the class
from lendingbot.modules.Lending import LendingEngine
from lendingbot.modules.Configuration import RootConfig, CoinConfig


@pytest.fixture
def mock_config():
    """Create a minimal RootConfig for testing."""
    config = RootConfig()
    # Add some default coin config for testing
    config.coin = {
        "BTC": CoinConfig(min_daily_rate=Decimal("0.01")),
        "default": CoinConfig()
    }
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

