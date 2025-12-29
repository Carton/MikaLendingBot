"""
Pytest configuration and fixtures for integration tests.

Integration tests make real API calls to exchanges and require:
- Valid API credentials in default.cfg
- Network connectivity
- Respect for rate limits

Run with: RUN_INTEGRATION_TESTS=true pytest tests/integration/
"""

import os
import sys
import time
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from lendingbot.modules import Configuration, Data
from lendingbot.modules.Logger import Logger
from lendingbot.modules.Bitfinex import Bitfinex
from lendingbot.modules.Poloniex import Poloniex


def pytest_configure(config):
    """Skip all integration tests if not enabled."""
    run_integration = os.getenv("RUN_INTEGRATION_TESTS", "false").lower() == "true"
    if not run_integration:
        pytest.skip("Integration tests disabled. Set RUN_INTEGRATION_TESTS=true")


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
