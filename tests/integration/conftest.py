"""
Pytest configuration and fixtures for integration tests.

Integration tests make real API calls to exchanges and require:
- Valid API credentials in default.cfg
- Network connectivity
- Respect for rate limits

Run with: RUN_INTEGRATION_TESTS=true pytest tests/integration/
"""

import time
from pathlib import Path

import pytest

from lendingbot.modules import Configuration, Data
from lendingbot.modules.Logger import Logger
from lendingbot.modules.Bitfinex import Bitfinex
from lendingbot.modules.Poloniex import Poloniex


@pytest.fixture(scope="module")
def config():
    """Load configuration for integration tests."""
    config_path = Path(__file__).parent.parent.parent / "default.cfg"

    # Initialize Data module first (required by Configuration)
    Data.init(None, None)

    # Load configuration
    cfg = Configuration
    cfg.init(str(config_path), Data)
    return cfg


@pytest.fixture(scope="module")
def logger():
    """Create logger instance for integration tests."""
    return Logger()


@pytest.fixture(scope="module")
def bitfinex_api(config, logger):
    """Create Bitfinex API instance for integration tests."""
    return Bitfinex(config, logger)


@pytest.fixture(scope="module")
def poloniex_api(config, logger):
    """Create Poloniex API instance for integration tests."""
    return Poloniex(config, logger)


@pytest.fixture(scope="module")
def start_time():
    """Record test start time for performance measurements."""
    return time.time()
