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
        # USD should be initialized from all_currencies, using default config
        assert "USD" in engine.coin_cfg
        assert engine.coin_cfg["USD"].min_daily_rate == Decimal("0.005")  # default
        assert engine.coin_cfg["USD"].strategy == LendingStrategy.SPREAD  # default
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

        # 1. Exact match at first element
        # gap_expected = 10 * 100 / 100 = 10
        # i=0, sum=10 >= 10. Returns rates[1] = 0.02
        assert engine.get_gap_rate("BTC", Decimal("10"), order_book, Decimal("100")) == Decimal(
            "0.02"
        )

        # 2. Match at second element
        # gap_expected = 15 * 100 / 100 = 15
        # i=0, sum=10 < 15
        # i=1, sum=20 >= 15. Returns rates[2] = 0.03
        assert engine.get_gap_rate("BTC", Decimal("15"), order_book, Decimal("100")) == Decimal(
            "0.03"
        )

        # 3. No match (beyond book total volume 50)
        # Hits request limit (5) and volume 50 < 60. Raises StopIteration
        with pytest.raises(StopIteration):
            engine.get_gap_rate("BTC", Decimal("60"), order_book, Decimal("100"))

        # 4. Match at last element
        # i=4, sum=50 >= 50. i+1 = 5 (beyond book). Returns max_daily_rate
        assert engine.get_gap_rate("BTC", Decimal("50"), order_book, Decimal("100")) == Decimal(
            "0.1"
        )

    def test_get_gap_mode_rates_relative(self, engine):
        engine.initialize()
        # Mock construct_order_books
        order_book = {"rates": [0.01, 0.02, 0.03], "volumes": [10, 10, 10]}
        with patch.object(engine, "construct_order_books", return_value=({}, order_book)):
            # Set explicit gap values on the engine directly
            engine.gap_mode_default = "relative"
            engine.gap_bottom_default = Decimal("10")
            engine.gap_top_default = Decimal("100")

            # Ensure BTC specific config doesn't interfere
            if "BTC" in engine.coin_cfg:
                engine.coin_cfg["BTC"].gap_bottom = Decimal("0")

            # total balance 100 -> depth 10 and 100
            rates = engine.get_gap_mode_rates("BTC", Decimal("100"), Decimal("100"), {})
            # rates[0] is top_rate, rates[1] is bottom_rate

            # depth 10 -> bottom_rate = rates[1] = 0.02 (returns rates[i+1] when i=0)
            assert rates[1] == Decimal("0.02")
            # depth 100 -> top_rate = rates[0] = max_daily_rate = 5.0
            assert rates[0] == Decimal("5.0")

    def test_get_gap_mode_rates_rawbtc(self, engine):
        engine.initialize()
        # ETH ticker: 0.05 BTC/ETH
        ticker = {"BTC_ETH": {"last": "0.05"}}
        # depth in ETH: bottom = 0.5 / 0.05 = 10 ETH, top = 1.0 / 0.05 = 20 ETH

        order_book = {"rates": [0.01, 0.02, 0.03, 0.04], "volumes": [15, 10, 10, 10]}
        with patch.object(engine, "construct_order_books", return_value=({}, order_book)):
            # Force defaults for this test
            engine.gap_mode_default = "rawbtc"
            engine.gap_bottom_default = Decimal("0.5")  # 0.5 BTC
            engine.gap_top_default = Decimal("1.0")  # 1.0 BTC

            # Ensure ETH specific config doesn't interfere
            if "ETH" in engine.coin_cfg:
                engine.coin_cfg["ETH"].gap_bottom = Decimal("0")

            rates = engine.get_gap_mode_rates("ETH", Decimal("100"), Decimal("100"), ticker)
            # bottom depth 10 -> 15 >= 10 -> i=0. Returns rates[1] = 0.02
            # top depth 20 -> 15 < 20 < 25 -> i=1. Returns rates[2] = 0.03
            assert rates[1] == Decimal("0.02")
            assert rates[0] == Decimal("0.03")

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

    def test_adjust_rate_for_competition(self, engine):
        # Above threshold
        assert engine._adjust_rate_for_competition(0.01) == pytest.approx(0.009999)
        # Below threshold
        assert engine._adjust_rate_for_competition(0.00005) == 0.00005
        # At threshold
        assert engine._adjust_rate_for_competition(0.0001) == 0.0001

    def test_calculate_duration_no_thresholds(self, engine):
        engine.xday_threshold = ""
        # Default behavior when no thresholds defined
        assert engine._calculate_duration(0.01, "2") == "2"
        assert engine._calculate_duration(0.01, "5") == "5"

    def test_calculate_duration_with_thresholds(self, engine):
        # 0.05% -> 25 days, 0.1% -> 60 days
        # Internal representation is percentage / 100
        engine.xday_threshold = "0.05:25,0.1:60"

        # Rate below first threshold -> use first threshold days
        assert engine._calculate_duration(0.0004, "2") == "25"

        # Rate at threshold -> use threshold days
        assert engine._calculate_duration(0.0005, "2") == "25"
        assert engine._calculate_duration(0.001, "2") == "60"

        # Rate between thresholds -> interpolation
        # (0.0005+0.001)/2 = 0.00075 -> (25+60)/2 = 42.5 -> "42"
        assert engine._calculate_duration(0.00075, "2") == "42"

        # Rate above last threshold -> use last threshold days
        assert engine._calculate_duration(0.002, "2") == "60"

        # Explicit days override interpolation
        assert engine._calculate_duration(0.001, "5") == "5"

    def test_calculate_duration_with_end_date(self, engine, mock_data):
        engine.config.bot.end_date = "2026-01-10"
        # mock_data.get_max_duration returns days remaining
        mock_data.get_max_duration.return_value = 3

        # Duration restricted by end_date
        assert engine._calculate_duration(0.001, "5") == "3"
        assert engine._calculate_duration(0.001, "2") == "2"  # default 2 is less than 3


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

    def test_cancel_all_api_error(self, engine, mock_api):
        engine.initialize()
        mock_api.return_open_loan_offers.return_value = {"BTC": [{"id": 123, "amount": "1.0"}]}
        mock_api.return_available_account_balances.return_value = {"lending": {"BTC": "0.0"}}

        # Simulate API error during cancel
        mock_api.cancel_loan_offer.side_effect = Exception("API Down")

        # Should not crash, just log error
        engine.cancel_all()
        mock_api.cancel_loan_offer.assert_called()
        engine.log.log.assert_called_with("Error canceling loan offer: API Down")

    def test_lend_cur_empty_books(self, engine, mock_api):  # noqa: ARG002
        engine.initialize()
        # Mock construct_order_books to return empty books
        with patch.object(engine, "construct_order_books", return_value=({}, {})):
            total_lent_info = MagicMock()
            total_lent_info.total_lent = {"BTC": Decimal("0")}
            lending_balances = {"BTC": "1.0"}

            # Should return 0 (no currencies usable) and not crash
            result = engine.lend_cur("BTC", total_lent_info, lending_balances, {})
            assert result == 0

    def test_lend_cur_api_exception(self, engine, mock_api):  # noqa: ARG002
        engine.initialize()
        # Mock construct_order_books to return valid books but create_lend_offer raises non-amount error
        order_book = {"rates": [0.01], "volumes": [10]}
        with (
            patch.object(engine, "construct_order_books", return_value=({}, order_book)),
            patch.object(engine, "create_lend_offer", side_effect=RuntimeError("Serious Error")),
        ):
            total_lent_info = MagicMock()
            total_lent_info.total_lent = {"BTC": Decimal("0")}
            lending_balances = {"BTC": "1.0"}

            with pytest.raises(RuntimeError, match="Serious Error"):
                engine.lend_cur("BTC", total_lent_info, lending_balances, {})
