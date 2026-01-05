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
def test_lending_engine_init(mock_config, mock_data, mock_logger, mock_api):
    """Test that LendingEngine initializes correctly with dependencies."""
    engine = LendingEngine(mock_config, mock_data, mock_logger, mock_api)
    
    assert engine.config == mock_config
    assert engine.data == mock_data
    assert engine.log == mock_logger
    assert engine.api == mock_api
    
    # Check that core state attributes are initialized
    assert hasattr(engine, 'coin_cfg')
    assert hasattr(engine, 'loans_provided')
