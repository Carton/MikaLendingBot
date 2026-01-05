from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from lendingbot.modules.Configuration import (
    CoinConfig,
    Exchange,
    GapMode,
    LendingStrategy,
    RootConfig,
)
from lendingbot.modules.Lending import LendingEngine


@pytest.fixture
def mock_config():
    """Create a comprehensive RootConfig for testing."""
    config = RootConfig()
    config.api.exchange = Exchange.BITFINEX
    config.api.all_currencies = ["BTC", "ETH", "USD"]
    config.bot.period_active = 60
    config.bot.period_inactive = 300

    # Default coin config
    config.coin["default"] = CoinConfig(
        min_daily_rate=Decimal("0.005"),
        max_daily_rate=Decimal("5.0"),
        spread_lend=3,
        gap_mode=GapMode.RELATIVE,
        gap_bottom=Decimal("10"),
        gap_top=Decimal("100"),
    )

    # Specific coin config
    config.coin["BTC"] = CoinConfig(
        min_daily_rate=Decimal("0.01"), strategy=LendingStrategy.SPREAD, spread_lend=5
    )

    config.coin["ETH"] = CoinConfig(
        min_daily_rate=Decimal("0.001"),
        strategy=LendingStrategy.FRR,
        frr_delta_min=Decimal("-5"),
        frr_delta_max=Decimal("5"),
    )

    return config


@pytest.fixture
def mock_api():
    api = MagicMock()
    api.return_ticker.return_value = {"BTC_ETH": {"last": "0.05"}}
    return api


@pytest.fixture
def mock_log():
    return MagicMock()


@pytest.fixture
def mock_data():
    data = MagicMock()
    data.truncate.side_effect = lambda v, p: round(v, p)
    return data


@pytest.fixture
def engine(mock_config, mock_api, mock_log, mock_data):
    """LendingEngine instance with mocked dependencies."""
    # Reset globals before each test if using wrappers, but here we test the class directly.
    return LendingEngine(mock_config, mock_api, mock_log, mock_data)


class TestLendingEngineInit:
    """Tests for initialization and basic properties (from precedence and core)."""

    def test_init_state(self, engine, mock_config):
        assert engine.config == mock_config
        assert engine.sleep_time == 0
        assert engine.lending_paused is False

    def test_initialize_from_config(self, engine):
        engine.initialize(dry_run=True)
        assert engine.dry_run is True
        # BTC specific value
        assert engine.coin_cfg["BTC"].min_daily_rate == Decimal("0.01")
        # Default value
        assert engine.min_daily_rate == Decimal("0.005")
        assert engine.sleep_time == 60

    def test_web_settings_precedence(self, engine):
        # Mock WebServer.get_web_settings
        web_settings = {"frrdelta_min": -20, "frrdelta_max": 20, "lending_paused": True}
        with patch("lendingbot.modules.WebServer.get_web_settings", return_value=web_settings):
            engine.initialize()
            assert engine.frrdelta_min == Decimal("-20")
            assert engine.frrdelta_max == Decimal("20")
            assert engine.lending_paused is True


class TestLendingEngineLogic:
    """Tests for core business logic (from core and strategy)."""

    def test_get_min_loan_size(self, engine):
        engine.min_loan_size = Decimal("0.01")
        engine.min_loan_sizes = {"BTC": Decimal("0.05")}

        assert engine.get_min_loan_size("BTC") == Decimal("0.05")
        assert engine.get_min_loan_size("ETH") == Decimal("0.01")

    def test_get_gap_rate(self, engine):
        engine.loan_orders_request_limit["BTC"] = 5
        engine.max_daily_rate = Decimal("0.1")

        order_book = {"rates": [0.01, 0.02, 0.03, 0.04, 0.05], "volumes": [10, 10, 10, 10, 10]}

        # Relative Gap 15% of total 100 -> depth 15
        # Index 0: 10 < 15
        # Index 1: 20 >= 15 -> returns rates[2] = 0.03 (based on original loop logic)
        rate = engine.get_gap_rate("BTC", Decimal("15"), order_book, Decimal("100"))
        assert rate == Decimal("0.03")

    def test_get_cur_spread(self, engine):
        engine.min_loan_size = Decimal("0.01")
        # Bal 0.05, want spread 10. 5 * 0.01 = 0.05. Max spread possible is 5.
        assert engine.get_cur_spread(10, Decimal("0.05"), "BTC") == 5
        # Bal 1.0, want 10. Possible.
        assert engine.get_cur_spread(10, Decimal("1.0"), "BTC") == 10

    def test_get_frr_or_min_daily_rate_non_frr(self, engine):
        engine.initialize()
        # BTC is SPREAD
        rate_info = engine.get_frr_or_min_daily_rate("BTC")
        assert rate_info.final_rate == Decimal("0.01")
        assert rate_info.frr_enabled is False

    def test_get_frr_or_min_daily_rate_bitfinex_frr(self, engine, mock_api):
        engine.initialize()
        # ETH is FRR
        mock_api.get_frr.return_value = 0.002  # 0.2%
        # frr_delta_min/max are -5 to 5. Step 0 (start) is -5%
        # Final rate = 0.002 * (1 - 0.05) = 0.0019
        rate_info = engine.get_frr_or_min_daily_rate("ETH")

        assert rate_info.frr_enabled is True
        assert float(rate_info.final_rate) == pytest.approx(0.0019)
        assert rate_info.frr_used is True  # 0.0019 > min_rate 0.001

    def test_create_lend_offer_adjustment(self, engine, mock_api):
        engine.initialize()
        engine.create_lend_offer("BTC", Decimal("1"), Decimal("0.01"))

        mock_api.create_loan_offer.assert_called_once()
        args = mock_api.create_loan_offer.call_args[0]
        # rate 0.01 > 0.0001 -> adjusted to 0.009999
        assert float(args[4]) == pytest.approx(0.009999)


class TestLendingEngineFlow:
    """Tests for high-level flow (from comprehensive)."""

    def test_lend_all_dry_run(self, engine, mock_data, mock_api):
        engine.initialize(dry_run=True)
        # Mock Data behavior for dry run
        mock_data.get_total_lent.return_value.total_lent = {"BTC": Decimal("10")}
        mock_data.get_on_order_balances.return_value = {"BTC": "1.0"}

        # Mock order books
        order_book = {"rates": [0.02], "volumes": [10]}
        demand_book = {"rates": [0.015], "volumes": [5], "rangeMax": [2]}

        with patch.object(engine, "construct_order_books", return_value=[demand_book, order_book]):
            engine.lend_all()

        # Should NOT call API create_loan_offer because dry_run=True
        mock_api.create_loan_offer.assert_not_called()

    def test_cancel_all(self, engine, mock_api):
        engine.initialize()
        mock_api.return_open_loan_offers.return_value = {"BTC": [{"id": 123, "amount": "1.0"}]}
        mock_api.return_available_account_balances.return_value = {"lending": {"BTC": "0.0"}}

        engine.cancel_all()
        mock_api.cancel_loan_offer.assert_called_with("BTC", 123)
