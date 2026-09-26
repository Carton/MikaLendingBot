import datetime as dt
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from lendingbot.modules.Configuration import (
    CancelPolicy,
    CoinConfig,
    Exchange,
    GapMode,
    LendingStrategy,
    RootConfig,
    XDayThreshold,
)
from lendingbot.modules.Lending import LendingEngine
from lendingbot.modules.OfferRegistry import STATUS_CANCEL_PENDING


def timestamp(value: str) -> float:
    return dt.datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=dt.UTC).timestamp()


@pytest.fixture
def mock_config(tmp_path):
    """Create a comprehensive RootConfig for testing."""
    config = RootConfig()
    config.api.exchange = Exchange.BITFINEX
    config.api.all_currencies = ["BTC", "ETH", "USD"]
    config.bot.period_active = 60
    config.bot.period_inactive = 300
    config.bot.offer_registry_file = str(tmp_path / "offer_registry.json")

    # Default coin config
    config.coin["default"] = CoinConfig(
        min_daily_rate=Decimal("0.5"),  # 0.5% -> 0.005
        max_daily_rate=Decimal("5.0"),  # 5% -> 0.05
        spread_lend=3,
        gap_mode=GapMode.RELATIVE,
        gap_bottom=Decimal("10"),
        gap_top=Decimal("100"),
    )

    # Specific coin config
    config.coin["BTC"] = CoinConfig(
        # 1% -> 0.01
        min_daily_rate=Decimal("1.0"),
        strategy=LendingStrategy.SPREAD,
        spread_lend=5,
    )

    config.coin["ETH"] = CoinConfig(
        # 0.1% -> 0.001
        min_daily_rate=Decimal("0.1"),
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

    def test_web_settings_xday_precedence(self, engine):
        web_settings = {
            "xday_thresholds": [
                {"rate": 0.06, "days": 90},
                {"rate": 0.03, "days": 30},
            ]
        }
        with patch("lendingbot.modules.WebServer.get_web_settings", return_value=web_settings):
            engine.initialize()
            assert engine.has_web_xday_override is True
            assert [(t.rate, t.days) for t in engine.xday_thresholds] == [
                (Decimal("0.03"), 30),
                (Decimal("0.06"), 90),
            ]
            # The web thresholds drive duration calculation
            assert engine._calculate_duration(0.0002, "2") == "30"
            assert engine._calculate_duration(0.0008, "2") == "90"

    def test_web_settings_without_xday_keeps_toml_thresholds(self, engine, mock_config):
        mock_config.coin["default"].xday_thresholds = [
            XDayThreshold(rate=Decimal("0.05"), days=25),
        ]
        with patch("lendingbot.modules.WebServer.get_web_settings", return_value={}):
            engine.initialize()
            assert engine.has_web_xday_override is False
            assert engine._calculate_duration(0.0005, "2") == "25"


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
            # depth 100 -> top_rate = rates[0] = max_daily_rate = 5.0 -> 0.05
            assert rates[0] == Decimal("0.05")

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
        with patch("lendingbot.modules.WebServer.get_web_settings", return_value={}):
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

    def test_create_lend_offer_notifies_at_max_xday_threshold(self, engine):
        engine.initialize()
        engine.xday_thresholds = [
            XDayThreshold(rate=Decimal("0.05"), days=25),
            XDayThreshold(rate=Decimal("0.1"), days=60),
        ]
        engine.config.notifications.notify_xday_threshold = True

        # Rate above the last threshold -> 60 days -> notify
        engine.create_lend_offer("BTC", Decimal("1"), Decimal("0.002"))
        assert engine.log.notify.call_count == 1
        assert "60 days" in engine.log.notify.call_args[0][0]

        # Rate mapping below the last threshold -> no additional notify
        engine.create_lend_offer("BTC", Decimal("1"), Decimal("0.0004"))
        assert engine.log.notify.call_count == 1

    def test_adjust_rate_for_competition(self, engine):
        # Above threshold
        assert engine._adjust_rate_for_competition(0.01) == pytest.approx(0.009999)
        # Below threshold
        assert engine._adjust_rate_for_competition(0.00005) == 0.00005
        # At threshold
        assert engine._adjust_rate_for_competition(0.0001) == 0.0001

    def test_calculate_duration_no_thresholds(self, engine):
        engine.xday_thresholds = []
        # Default behavior when no thresholds defined
        assert engine._calculate_duration(0.01, "2") == "2"
        assert engine._calculate_duration(0.01, "5") == "5"

    def test_calculate_duration_with_thresholds(self, engine):
        # 0.05% -> 25 days, 0.1% -> 60 days (rates are daily percentages)
        engine.xday_thresholds = [
            XDayThreshold(rate=Decimal("0.05"), days=25),
            XDayThreshold(rate=Decimal("0.1"), days=60),
        ]

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

    def test_construct_orders_max_offer_size_unlimited(self, engine):
        engine.initialize()
        engine.coin_cfg["BTC"].max_offer_size = Decimal("0")
        # Ensure spread allows 3 orders
        engine.spread_lend = 3
        # Mock gap rates
        with patch.object(
            engine, "get_gap_mode_rates", return_value=[Decimal("0.05"), Decimal("0.01")]
        ):
            # cur_active_bal = 300. Expect 3 orders of 100.
            resp = engine.construct_orders("BTC", Decimal("300"), Decimal("1000"), {})
            assert len(resp["amounts"]) == 3
            assert all(amt == Decimal("100") for amt in resp["amounts"])

    def test_construct_orders_max_offer_size_limited(self, engine):
        engine.initialize()
        engine.coin_cfg["BTC"].max_offer_size = Decimal("50")
        engine.spread_lend = 3
        with patch.object(
            engine, "get_gap_mode_rates", return_value=[Decimal("0.05"), Decimal("0.01")]
        ):
            # cur_active_bal = 300. Normally 100 per order, but capped at 50.
            resp = engine.construct_orders("BTC", Decimal("300"), Decimal("1000"), {})
            assert len(resp["amounts"]) == 3
            assert all(amt == Decimal("50") for amt in resp["amounts"])
            # The remaining 150 is left un-lent (handled correctly by only offering sum(amounts)).

    def test_construct_orders_max_offer_size_with_remainder(self, engine):
        engine.initialize()
        engine.coin_cfg["BTC"].max_offer_size = Decimal("105")
        engine.spread_lend = 3
        with patch.object(
            engine, "get_gap_mode_rates", return_value=[Decimal("0.05"), Decimal("0.01")]
        ):
            # cur_active_bal = 310.
            # 310 / 3 = 103.33333333.
            # Amounts before remainder: [103.33333333, 103.33333333, 103.33333333]
            # Remainder: 310 - 309.99999999 = 0.00000001
            # Allowance on first order: 105 - 103.33333333 = 1.66666667
            # So remainder is fully added to the first order.
            resp = engine.construct_orders("BTC", Decimal("310"), Decimal("1000"), {})
            assert len(resp["amounts"]) == 3
            assert resp["amounts"][0] == Decimal("103.33333334")
            assert resp["amounts"][1] == Decimal("103.33333333")
            assert resp["amounts"][2] == Decimal("103.33333333")

    def test_construct_orders_max_offer_size_remainder_capped(self, engine):
        engine.initialize()
        # Cap exactly at the truncated amount
        engine.coin_cfg["BTC"].max_offer_size = Decimal("103.33333333")
        engine.spread_lend = 3
        with patch.object(
            engine, "get_gap_mode_rates", return_value=[Decimal("0.05"), Decimal("0.01")]
        ):
            # cur_active_bal = 310.
            # Remainder is 0.00000001, but allowance is 0.
            resp = engine.construct_orders("BTC", Decimal("310"), Decimal("1000"), {})
            assert resp["amounts"][0] == Decimal("103.33333333")  # Can't add remainder

    def test_notify_new_loans_records_only_loans_after_baseline(self, engine, mock_api):
        engine.config.bot.web.recent_successful_loans = 3
        existing = {
            "id": 1,
            "currency": "USD",
            "rate": "0.00031",
            "amount": "100.0",
            "duration": "2",
            "date": "2026-05-24 09:00:00",
        }
        new_first = {
            "id": 2,
            "currency": "USD",
            "rate": "0.00032",
            "amount": "200.0",
            "duration": "2",
            "date": "2026-05-24 09:05:00",
        }
        new_second = {
            "id": 3,
            "currency": "USD",
            "rate": "0.00033",
            "amount": "300.0",
            "duration": "2",
            "date": "2026-05-24 09:06:00",
        }
        mock_api.return_active_loans.side_effect = [
            {"provided": [existing]},
            {"provided": [existing, new_first, new_second]},
        ]

        with patch(
            "lendingbot.modules.Lending.time.time",
            return_value=timestamp("2026-05-24 09:01:00"),
        ):
            engine.notify_new_loans(60)
            assert engine.get_recent_successful_loans(limit=3) == {}

            engine.notify_new_loans(60)

        assert engine.get_recent_successful_loans(limit=3) == {
            "USD": [
                {
                    "amount": "300.0",
                    "rate": "0.00033",
                    "date": "2026-05-24 09:06:00",
                },
                {
                    "amount": "200.0",
                    "rate": "0.00032",
                    "date": "2026-05-24 09:05:00",
                },
            ]
        }

    def test_notify_new_loans_dedupes_business_loan_when_id_changes(self, engine, mock_api):
        engine.config.bot.web.recent_successful_loans = 3
        new_loan = {
            "id": 2,
            "currency": "USD",
            "rate": "0.0003980",
            "amount": "8919.57146463",
            "duration": "2",
            "date": "2026-05-29 15:22:17",
        }
        repeated_loan = dict(new_loan, id="changed-id")
        mock_api.return_active_loans.side_effect = [
            {"provided": []},
            {"provided": [new_loan]},
            {"provided": [repeated_loan]},
        ]

        with patch(
            "lendingbot.modules.Lending.time.time",
            return_value=timestamp("2026-05-29 15:20:00"),
        ):
            engine.notify_new_loans(60)
            engine.notify_new_loans(60)
            engine.notify_new_loans(60)

        assert engine.get_recent_successful_loans(limit=3) == {
            "USD": [
                {
                    "amount": "8919.57146463",
                    "rate": "0.0003980",
                    "date": "2026-05-29 15:22:17",
                }
            ]
        }

    def test_notify_new_loans_skips_existing_active_loan_when_id_changes(self, engine, mock_api):
        engine.config.bot.web.recent_successful_loans = 3
        existing = {
            "id": "baseline-id",
            "currency": "USD",
            "rate": "0.0003938",
            "amount": "187.75710464",
            "duration": "2",
            "date": "2026-05-21 13:58:51",
        }
        same_existing_loan = dict(existing, id="changed-id")
        mock_api.return_active_loans.side_effect = [
            {"provided": [existing]},
            {"provided": [same_existing_loan]},
        ]

        with patch(
            "lendingbot.modules.Lending.time.time",
            return_value=timestamp("2026-05-29 15:20:00"),
        ):
            engine.notify_new_loans(60)
            engine.notify_new_loans(60)

        assert engine.get_recent_successful_loans(limit=3) == {}

    def test_start_scheduler_initializes_recent_loan_baseline_immediately(self, engine, mock_api):
        engine.config.bot.web.enabled = True
        engine.config.bot.web.recent_successful_loans = 3
        engine.config.notifications.notify_new_loans = False
        engine.scheduler = MagicMock()
        engine.scheduler.empty.return_value = True
        mock_api.return_active_loans.return_value = {
            "provided": [
                {
                    "id": "baseline-id",
                    "currency": "USD",
                    "rate": "0.0003938",
                    "amount": "187.75710464",
                    "duration": "2",
                    "date": "2026-05-21 13:58:51",
                }
            ]
        }

        with patch(
            "lendingbot.modules.Lending.time.time",
            return_value=timestamp("2026-05-29 15:20:00"),
        ):
            engine.start_scheduler()

        mock_api.return_active_loans.assert_called_once_with()
        assert engine.get_recent_successful_loans(limit=3) == {}

    def test_notify_new_loans_records_duplicate_active_loan_once(self, engine, mock_api):
        engine.config.bot.web.recent_successful_loans = 3
        existing = {
            "id": 1,
            "currency": "USD",
            "rate": "0.00031",
            "amount": "100.0",
            "duration": "2",
            "date": "2026-05-24 09:00:00",
        }
        new_loan = {
            "id": 2,
            "currency": "USD",
            "rate": "0.00032",
            "amount": "200.0",
            "duration": "2",
            "date": "2026-05-24 09:05:00",
        }
        mock_api.return_active_loans.side_effect = [
            {"provided": [existing]},
            {"provided": [existing, new_loan, dict(new_loan)]},
        ]

        with patch(
            "lendingbot.modules.Lending.time.time",
            return_value=timestamp("2026-05-24 09:01:00"),
        ):
            engine.notify_new_loans(60)
            engine.notify_new_loans(60)

        assert engine.get_recent_successful_loans(limit=3) == {
            "USD": [
                {
                    "amount": "200.0",
                    "rate": "0.00032",
                    "date": "2026-05-24 09:05:00",
                }
            ]
        }

    def test_notify_new_loans_normalizes_active_loan_ids(self, engine, mock_api):
        engine.config.bot.web.recent_successful_loans = 3
        existing = {
            "id": 1,
            "currency": "USD",
            "rate": "0.00031",
            "amount": "100.0",
            "duration": "2",
            "date": "2026-05-24 09:00:00",
        }
        new_loan = {
            "id": 2,
            "currency": "USD",
            "rate": "0.00032",
            "amount": "200.0",
            "duration": "2",
            "date": "2026-05-24 09:05:00",
        }
        repeated_loan = dict(new_loan, id="2")
        mock_api.return_active_loans.side_effect = [
            {"provided": [existing]},
            {"provided": [existing, new_loan]},
            {"provided": [existing, repeated_loan]},
        ]

        with patch(
            "lendingbot.modules.Lending.time.time",
            return_value=timestamp("2026-05-24 09:01:00"),
        ):
            engine.notify_new_loans(60)
            engine.notify_new_loans(60)
            engine.notify_new_loans(60)

        assert engine.get_recent_successful_loans(limit=3) == {
            "USD": [
                {
                    "amount": "200.0",
                    "rate": "0.00032",
                    "date": "2026-05-24 09:05:00",
                }
            ]
        }

    def test_recent_successful_loans_are_capped_per_currency(self, engine):
        for index in range(7):
            engine.record_successful_loan(
                {
                    "id": index,
                    "currency": "USD",
                    "rate": f"0.0003{index}",
                    "amount": f"{index + 1}.0",
                    "date": f"2026-05-24 09:0{index}:00",
                }
            )

        recent = engine.get_recent_successful_loans(limit=6)

        assert len(recent["USD"]) == 6
        assert recent["USD"][0]["amount"] == "7.0"
        assert recent["USD"][-1]["amount"] == "2.0"


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
        engine.log.log.assert_called_with("Error canceling loan offer (outcome unknown): API Down")

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


@pytest.fixture
def limited_config(mock_config):
    """Config with cancel_policy=limited and valid coin settings for all currencies."""
    mock_config.bot.cancel_policy = CancelPolicy.LIMITED
    for symbol in ("BTC", "ETH", "USD"):
        mock_config.coin[symbol] = CoinConfig(
            min_daily_rate=Decimal("0.5"),
            strategy=LendingStrategy.FRR,
            max_offer_size=Decimal("20000"),
        )
    return mock_config


@pytest.fixture
def limited_engine(limited_config, mock_api, mock_log, mock_data):
    return LendingEngine(limited_config, mock_api, mock_log, mock_data)


class TestCancelPolicy:
    """Tests for cancel_policy ("all" / "limited") and offer registry integration."""

    @staticmethod
    def setup_open_offers(mock_api, offers, balances=None):
        mock_api.return_open_loan_offers.return_value = offers
        if balances is not None:
            mock_api.return_available_account_balances.return_value = {"lending": balances}
        mock_api.cancel_loan_offer.return_value = {"success": 1, "message": "cancelled"}

    # --- "all" (legacy) ---

    def test_policy_all_cancels_every_offer(self, engine, mock_api):
        engine.initialize()
        assert engine.offer_registry is not None
        engine.offer_registry.add("BTC", 101, "1.0", "0.0001", 2)

        self.setup_open_offers(
            mock_api,
            {"BTC": [{"id": 101, "amount": "1.0"}, {"id": 202, "amount": "5.0"}]},
            {"BTC": "0.0"},
        )

        engine.cancel_all()

        assert mock_api.cancel_loan_offer.call_args_list == [
            call("BTC", 101),
            call("BTC", 202),
        ]

    # --- "limited": refresh + absorb ---

    def test_limited_refreshes_own_and_absorbs_untracked(self, limited_engine, mock_api):
        limited_engine.initialize()
        assert limited_engine.offer_registry is not None
        limited_engine.offer_registry.add("BTC", 101, "12000", "0.0003", 30)

        mock_api.return_open_loan_offers.return_value = {
            "BTC": [{"id": 101, "amount": "12000"}, {"id": 202, "amount": "5000"}]
        }
        mock_api.return_available_account_balances.side_effect = [
            {"lending": {"BTC": "100"}},
            {"lending": {"BTC": "12100"}},
        ]
        mock_api.cancel_loan_offer.return_value = {"success": 1, "message": "cancelled"}

        limited_engine.cancel_all()

        # Own offer refreshed first, then the untracked offer absorbed for the gap.
        assert mock_api.cancel_loan_offer.call_args_list == [
            call("BTC", 101),
            call("BTC", 202),
        ]
        own = limited_engine.offer_registry.get("BTC", 101)
        assert own is not None
        assert own.status == STATUS_CANCEL_PENDING

    def test_limited_skips_untracked_when_balance_covers_target(self, limited_engine, mock_api):
        limited_engine.initialize()
        assert limited_engine.offer_registry is not None
        limited_engine.offer_registry.add("BTC", 101, "12000", "0.0003", 30)

        mock_api.return_open_loan_offers.return_value = {
            "BTC": [{"id": 101, "amount": "12000"}, {"id": 202, "amount": "30000"}]
        }
        mock_api.return_available_account_balances.side_effect = [
            {"lending": {"BTC": "25000"}},
            {"lending": {"BTC": "37000"}},
        ]
        mock_api.cancel_loan_offer.return_value = {"success": 1, "message": "cancelled"}

        limited_engine.cancel_all()

        assert mock_api.cancel_loan_offer.call_args_list == [call("BTC", 101)]

    def test_limited_absorbs_descending_then_carves_smallest_covering(
        self, limited_engine, mock_api
    ):
        limited_engine.initialize()
        mock_api.return_open_loan_offers.return_value = {
            "BTC": [
                {"id": 1, "amount": "6000", "rate": "0.0002", "duration": 30},
                {"id": 2, "amount": "15000", "rate": "0.0003", "duration": 60},
            ]
        }
        mock_api.return_available_account_balances.return_value = {"lending": {"BTC": "0"}}
        mock_api.cancel_loan_offer.return_value = {"success": 1, "message": "cancelled"}
        mock_api.create_loan_offer.return_value = {"success": 1, "orderId": 777}

        limited_engine.cancel_all()

        # 15000 absorbed first (fits the 20000 gap); 6000 does not fit the
        # remaining 5000 gap, so it is carved down to 1000.
        assert mock_api.cancel_loan_offer.call_args_list == [call("BTC", 2), call("BTC", 1)]
        args = mock_api.create_loan_offer.call_args[0]
        assert args[0] == "BTC"
        assert args[1] == pytest.approx(1000.0)
        assert args[2] == 30  # remainder keeps the carved offer's duration
        assert args[4] == pytest.approx(0.0002)  # ... and its exact rate

    def test_limited_carves_oversized_offer_and_preserves_remainder(self, limited_engine, mock_api):
        limited_engine.initialize()
        mock_api.return_open_loan_offers.return_value = {
            "BTC": [{"id": 202, "amount": "30000", "rate": "0.0311", "duration": 90}]
        }
        mock_api.return_available_account_balances.return_value = {"lending": {"BTC": "0.01"}}
        mock_api.cancel_loan_offer.return_value = {"success": 1, "message": "cancelled"}
        mock_api.create_loan_offer.return_value = {"success": 1, "orderId": 555}

        limited_engine.cancel_all()

        assert mock_api.cancel_loan_offer.call_args_list == [call("BTC", 202)]
        args = mock_api.create_loan_offer.call_args[0]
        assert args[1] == pytest.approx(10000.01)
        assert args[2] == 90
        assert args[4] == pytest.approx(0.0311)  # no compete adjustment on restore

        registry = limited_engine.offer_registry
        assert registry is not None
        assert registry.tracked_ids("BTC") == set()
        assert registry.preserved_ids("BTC") == {555}
        persisted = Path(limited_engine.config.bot.offer_registry_file).read_text(encoding="utf-8")
        assert '"managed": false' in persisted

    def test_limited_dust_guard_skips_currency(self, limited_engine, mock_api):
        limited_engine.initialize()
        self.setup_open_offers(
            mock_api,
            {"BTC": [{"id": 1, "amount": "0.004"}, {"id": 2, "amount": "0.004"}]},
            {"BTC": "0"},
        )

        limited_engine.cancel_all()

        mock_api.cancel_loan_offer.assert_not_called()

    def test_limited_skips_when_max_active_reached(self, limited_engine, mock_api):
        limited_engine.initialize()
        limited_engine.coin_cfg["BTC"].max_active_amount = Decimal("1000")
        limited_engine.data.get_total_lent.return_value.total_lent = {"BTC": Decimal("1000")}
        assert limited_engine.offer_registry is not None
        limited_engine.offer_registry.add("BTC", 101, "500", "0.0003", 30)

        self.setup_open_offers(mock_api, {"BTC": [{"id": 101, "amount": "500"}]}, {"BTC": "0"})

        limited_engine.cancel_all()

        mock_api.cancel_loan_offer.assert_not_called()

    def test_limited_below_target_log_deduped(self, limited_engine, mock_api):
        limited_engine.initialize()
        mock_api.return_open_loan_offers.return_value = {"BTC": []}
        mock_api.return_available_account_balances.return_value = {"lending": {"BTC": "150"}}

        limited_engine.cancel_all()
        limited_engine.cancel_all()

        logs = [
            c
            for c in limited_engine.log.log.call_args_list
            if "not fully fundable" in str(c.args[0])
        ]
        assert len(logs) == 1

    def test_limited_dry_run_cancels_nothing(self, limited_engine, mock_api):
        limited_engine.initialize(dry_run=True)
        assert limited_engine.offer_registry is not None
        limited_engine.offer_registry.add("BTC", 101, "12000", "0.0003", 30)

        self.setup_open_offers(
            mock_api,
            {"BTC": [{"id": 101, "amount": "12000"}, {"id": 202, "amount": "5000"}]},
            {"BTC": "0"},
        )

        limited_engine.cancel_all()

        mock_api.cancel_loan_offer.assert_not_called()
        mock_api.create_loan_offer.assert_not_called()
        assert not limited_engine.offer_registry.file_exists()

    def test_limited_cancel_marks_pending_and_reconcile_removes(
        self, limited_engine, mock_api, mock_config
    ):
        limited_engine.initialize()
        assert limited_engine.offer_registry is not None
        limited_engine.offer_registry.add("BTC", 101, "1.0", "0.0001", 2)

        mock_api.return_open_loan_offers.return_value = {"BTC": [{"id": 101, "amount": "1.0"}]}
        mock_api.return_available_account_balances.side_effect = [
            {"lending": {"BTC": "0"}},
            {"lending": {"BTC": "1.0"}},
        ]
        mock_api.cancel_loan_offer.return_value = {"success": 1, "message": "cancelled"}

        limited_engine.cancel_all()

        own = limited_engine.offer_registry.get("BTC", 101)
        assert own is not None
        assert own.status == STATUS_CANCEL_PENDING
        persisted = Path(mock_config.bot.offer_registry_file).read_text(encoding="utf-8")
        assert "BTC:101" in persisted

        # Next cycle the offer is gone from the exchange -> registry drops it.
        mock_api.return_available_account_balances.side_effect = None
        mock_api.return_available_account_balances.return_value = {"lending": {"BTC": "1.0"}}
        mock_api.return_open_loan_offers.return_value = {"BTC": []}

        limited_engine.cancel_all()

        assert limited_engine.offer_registry.get("BTC", 101) is None

    # --- validation and failure paths ---

    def test_limited_requires_max_offer_size(self, mock_config, mock_api, mock_log, mock_data):
        mock_config.bot.cancel_policy = CancelPolicy.LIMITED
        mock_config.coin["BTC"] = CoinConfig(
            min_daily_rate=Decimal("0.5"), strategy=LendingStrategy.FRR
        )

        engine = LendingEngine(mock_config, mock_api, mock_log, mock_data)

        with pytest.raises(ValueError, match="max_offer_size"):
            engine.initialize()

    def test_limited_requires_single_order_placement(
        self, mock_config, mock_api, mock_log, mock_data
    ):
        mock_config.bot.cancel_policy = CancelPolicy.LIMITED
        mock_config.coin["BTC"] = CoinConfig(
            min_daily_rate=Decimal("0.5"), max_offer_size=Decimal("1000")
        )

        engine = LendingEngine(mock_config, mock_api, mock_log, mock_data)

        with pytest.raises(ValueError, match="strategy='FRR'"):
            engine.initialize()

    def test_limited_validation_skips_disabled_currency(self, limited_engine):
        # A disabled coin (max_active_amount=0) must not block startup even
        # without a cap or FRR strategy.
        limited_engine.config.coin["ETH"] = CoinConfig(
            min_daily_rate=Decimal("0.5"), max_active_amount=Decimal("0")
        )

        limited_engine.initialize()  # must not raise

        assert limited_engine.registry_error is None

    def test_limited_skips_absorption_when_own_refresh_fails(self, limited_engine, mock_api):
        limited_engine.initialize()
        assert limited_engine.offer_registry is not None
        limited_engine.offer_registry.add("BTC", 101, "12000", "0.0003", 30)

        mock_api.return_open_loan_offers.return_value = {
            "BTC": [{"id": 101, "amount": "12000"}, {"id": 202, "amount": "5000"}]
        }
        mock_api.return_available_account_balances.return_value = {"lending": {"BTC": "0"}}
        mock_api.cancel_loan_offer.side_effect = Exception("API down")

        limited_engine.cancel_all()

        # Only the own refresh was attempted; the untracked offer is untouched.
        assert mock_api.cancel_loan_offer.call_args_list == [call("BTC", 101)]
        assert any(
            "skipping absorption and lending" in str(c.args[0])
            for c in limited_engine.log.log.call_args_list
        )

    def test_limited_carve_uses_actual_remaining_amount(self, limited_engine, mock_api):
        limited_engine.initialize()
        mock_api.return_open_loan_offers.return_value = {
            "BTC": [{"id": 202, "amount": "30000", "rate": "0.0311", "duration": 90}]
        }
        mock_api.return_available_account_balances.return_value = {"lending": {"BTC": "0.01"}}
        # The offer partially filled between snapshot and cancel: the exchange
        # only had 25000 left, so the restored remainder must shrink to match.
        mock_api.cancel_loan_offer.return_value = {
            "success": 1,
            "message": "cancelled",
            "remaining_amount": 25000,
        }
        mock_api.create_loan_offer.return_value = {"success": 1, "orderId": 556}

        limited_engine.cancel_all()

        args = mock_api.create_loan_offer.call_args[0]
        assert args[1] == pytest.approx(5000.01)  # 25000 - 19999.99 taken

    def test_limited_carve_cancel_failure_does_not_restore(self, limited_engine, mock_api):
        limited_engine.initialize()
        mock_api.return_open_loan_offers.return_value = {
            "BTC": [{"id": 202, "amount": "30000", "rate": "0.0311", "duration": 90}]
        }
        mock_api.return_available_account_balances.return_value = {"lending": {"BTC": "0.01"}}
        mock_api.cancel_loan_offer.return_value = {"success": 0, "message": "cancel rejected"}

        limited_engine.cancel_all()

        mock_api.cancel_loan_offer.assert_called_once()
        mock_api.create_loan_offer.assert_not_called()

    def test_restore_failure_is_logged_not_raised(self, limited_engine, mock_api):
        limited_engine.initialize()
        mock_api.return_open_loan_offers.return_value = {
            "BTC": [{"id": 202, "amount": "30000", "rate": "0.0311", "duration": 90}]
        }
        mock_api.return_available_account_balances.return_value = {"lending": {"BTC": "0.01"}}
        mock_api.cancel_loan_offer.return_value = {"success": 1, "message": "cancelled"}
        mock_api.create_loan_offer.side_effect = Exception("create failed")

        limited_engine.cancel_all()  # must not raise

        assert any(
            "Uncertain outcome restoring carved remainder" in str(c.args[0])
            for c in limited_engine.log.log.call_args_list
        )

    def test_restore_definite_failure_logged(self, limited_engine, mock_api):
        limited_engine.initialize()
        mock_api.return_open_loan_offers.return_value = {
            "BTC": [{"id": 202, "amount": "30000", "rate": "0.0311", "duration": 90}]
        }
        mock_api.return_available_account_balances.return_value = {"lending": {"BTC": "0.01"}}
        mock_api.cancel_loan_offer.return_value = {"success": 1, "message": "cancelled"}
        mock_api.create_loan_offer.return_value = {"success": 0, "orderId": 0}

        limited_engine.cancel_all()

        assert any(
            "Error restoring carved remainder" in str(c.args[0])
            for c in limited_engine.log.log.call_args_list
        )

    def test_limited_blocks_lending_when_own_refresh_fails(self, limited_engine, mock_api):
        limited_engine.initialize()
        assert limited_engine.offer_registry is not None
        limited_engine.offer_registry.add("BTC", 101, "12000", "0.0003", 30)

        mock_api.return_open_loan_offers.return_value = {
            "BTC": [{"id": 101, "amount": "12000"}, {"id": 202, "amount": "5000"}]
        }
        # Some free funds exist besides the stuck own offer.
        mock_api.return_available_account_balances.return_value = {"lending": {"BTC": "5000"}}
        mock_api.cancel_loan_offer.side_effect = Exception("API down")

        limited_engine.cancel_all()
        assert "BTC" in limited_engine._lending_blocked_currencies

        # Lending must not create a second slice next to the stuck one.
        mock_data = limited_engine.data
        mock_data.get_total_lent.return_value.total_lent = {"BTC": Decimal("0")}
        order_book = {"rates": [0.02], "volumes": [10]}
        demand_book = {"rates": [0.001], "volumes": [5], "rangeMax": [2]}
        with (
            patch.object(
                limited_engine, "construct_order_books", return_value=[demand_book, order_book]
            ),
            patch.object(limited_engine, "get_min_daily_rate", return_value=Decimal("0.001")),
        ):
            limited_engine.lend_all()

        mock_api.create_loan_offer.assert_not_called()
        assert any(
            "skipping lending this cycle" in str(c.args[0])
            for c in limited_engine.log.log.call_args_list
        )

    def test_limited_stops_absorption_on_unknown_cancel(self, limited_engine, mock_api):
        limited_engine.initialize()
        mock_api.return_open_loan_offers.return_value = {
            "BTC": [
                {"id": 1, "amount": "20000", "rate": "0.0003", "duration": 30},
                {"id": 2, "amount": "20000", "rate": "0.0003", "duration": 30},
            ]
        }
        mock_api.return_available_account_balances.return_value = {"lending": {"BTC": "0"}}
        # First cancel times out (outcome unknown): absorption must stop even
        # though the budget accounting has not consumed anything.
        mock_api.cancel_loan_offer.side_effect = [Exception("timed out"), {"success": 1}]

        limited_engine.cancel_all()

        assert mock_api.cancel_loan_offer.call_count == 1
        assert any(
            "stopping absorption for this cycle" in str(c.args[0])
            for c in limited_engine.log.log.call_args_list
        )
        mock_api.create_loan_offer.assert_not_called()  # no carve after unknown

    def test_limited_skips_when_target_below_min_size(self, limited_engine, mock_api):
        limited_engine.initialize()
        limited_engine.coin_cfg["BTC"].max_offer_size = Decimal("100")
        limited_engine.min_loan_sizes["BTC"] = Decimal("150")
        assert limited_engine.offer_registry is not None
        limited_engine.offer_registry.add("BTC", 101, "500", "0.0003", 30)

        self.setup_open_offers(mock_api, {"BTC": [{"id": 101, "amount": "500"}]}, {"BTC": "0"})

        limited_engine.cancel_all()

        mock_api.cancel_loan_offer.assert_not_called()

    def test_registry_error_skips_cancel_and_lending(self, engine, mock_api):
        engine.initialize()
        engine.registry_error = "registry file is corrupt"

        engine.cancel_all()
        mock_api.return_open_loan_offers.assert_not_called()

        engine.lend_all()
        engine.data.get_total_lent.assert_not_called()
        assert engine.sleep_time == engine.config.bot.period_inactive

    def test_initialize_with_corrupt_registry_sets_error_in_limited_mode(
        self, limited_engine, mock_config
    ):
        Path(mock_config.bot.offer_registry_file).write_text("{corrupt", encoding="utf-8")

        limited_engine.initialize()

        assert limited_engine.registry_error is not None
        assert limited_engine.offer_registry is None
        limited_engine.log.log_error.assert_called_once()

    def test_initialize_with_corrupt_registry_warns_only_in_all_mode(self, engine, mock_config):
        Path(mock_config.bot.offer_registry_file).write_text("{corrupt", encoding="utf-8")

        engine.initialize()

        # "all" does not depend on the registry for safety: keep lending.
        assert engine.registry_error is None
        assert engine.offer_registry is None
        engine.log.log_error.assert_not_called()
        assert any(
            "Offer registry unavailable" in str(c.args[0]) for c in engine.log.log.call_args_list
        )

    def test_reconcile_error_pauses_cancel_and_lending(self, limited_engine, mock_api):
        limited_engine.initialize()
        assert limited_engine.offer_registry is not None
        limited_engine.offer_registry.add("BTC", 101, "1.0", "0.0001", 2)

        # Snapshot carries a non-numeric amount -> reconcile must fail closed.
        self.setup_open_offers(
            mock_api, {"BTC": [{"id": 101, "amount": "not-a-number"}]}, {"BTC": "0"}
        )

        limited_engine.cancel_all()

        mock_api.cancel_loan_offer.assert_not_called()
        assert limited_engine.registry_error is not None
        limited_engine.lend_all()
        limited_engine.data.get_total_lent.assert_not_called()

    # --- offer registration ---

    def test_create_lend_offer_handles_poloniex_orderid_key(self, engine, mock_api):
        engine.initialize()
        mock_api.create_loan_offer.return_value = {"success": 1, "orderID": 888}

        engine.create_lend_offer("BTC", Decimal("1"), Decimal("0.01"))

        assert engine.offer_registry is not None
        assert engine.offer_registry.tracked_ids("BTC") == {888}

    def test_registry_persist_failure_stops_offer_recording(self, engine, mock_api):
        engine.initialize()
        mock_api.create_loan_offer.return_value = {"success": 1, "orderId": 999}
        assert engine.offer_registry is not None
        engine.offer_registry.persist = MagicMock(side_effect=OSError("disk full"))

        # The offer is created (and logged) first; the persist failure then
        # aborts the cycle by propagating.
        with pytest.raises(OSError, match="disk full"):
            engine.create_lend_offer("BTC", Decimal("1"), Decimal("0.01"))
        engine.log.offer.assert_called_once()
        assert engine.offer_registry.tracked_ids("BTC") == {999}

    def test_create_lend_offer_registers_order(self, engine, mock_api, mock_config):
        engine.initialize()
        mock_api.create_loan_offer.return_value = {"success": 1, "orderId": 777}

        engine.create_lend_offer("BTC", Decimal("1"), Decimal("0.01"))

        assert engine.offer_registry is not None
        assert engine.offer_registry.tracked_ids("BTC") == {777}
        persisted = Path(mock_config.bot.offer_registry_file).read_text(encoding="utf-8")
        assert "BTC:777" in persisted

    def test_create_lend_offer_without_order_id_is_not_tracked(self, engine, mock_api):
        engine.initialize()
        mock_api.create_loan_offer.return_value = {"success": 1, "message": "no id"}

        engine.create_lend_offer("BTC", Decimal("1"), Decimal("0.01"))

        assert engine.offer_registry is not None
        assert engine.offer_registry.order_count() == 0
        engine.log.log.assert_any_call(
            "[BTC] Offer placed but the response had no order id; "
            "it cannot be tracked by cancel_policy=limited"
        )
