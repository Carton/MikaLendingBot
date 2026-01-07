"""
Pytest configuration and fixtures for integration tests.

Integration tests make real API calls to exchanges and require:
- Valid API credentials in default.cfg
- Network connectivity
- Respect for rate limits

Run with: pytest --run-integration tests/integration/
"""

import time
from pathlib import Path

import pytest

from lendingbot.modules import Configuration
from lendingbot.modules.Bitfinex import Bitfinex
from lendingbot.modules.Logger import Logger
from lendingbot.modules.Poloniex import Poloniex


@pytest.fixture(scope="module")
def config():
    """Load configuration for integration tests.
    Tries config.toml first, then config_sample.toml.
    """
    root_dir = Path(__file__).parent.parent.parent
    config_path = root_dir / "config.toml"
    if not config_path.exists():
        config_path = root_dir / "config_sample.toml"

    # Load configuration using the new TOML loader
    return Configuration.load_config(config_path)


@pytest.fixture(scope="module")
def logger(config):
    """Create logger instance for integration tests."""
    return Logger(
        json_file=config.bot.json_file,
        json_log_size=config.bot.json_log_size,
        exchange=config.api.exchange.value,
        label=config.bot.label
    )


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
