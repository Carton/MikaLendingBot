"""
Tests for Lending module core logic.
"""

from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch

import pytest

from lendingbot.modules import Lending


@pytest.fixture
def lending_module():
    # Reset globals using the new function
    Lending._reset_globals()

    # Setup basic required globals for tests
    Lending.min_loan_size = Decimal("0.01")
    Lending.loanOrdersRequestLimit = {}
    Lending.defaultLoanOrdersRequestLimit = 5
    Lending.max_daily_rate = Decimal("0.05")  # 5%
    Lending.log = MagicMock()

    from lendingbot.modules import Data

    Lending.Data = Data

    return Lending


class TestLendingCore:
    def test_get_min_loan_size_default(self, lending_module):
        lending_module.min_loan_sizes = {}
        lending_module.min_loan_size = Decimal("0.01")
        assert lending_module.get_min_loan_size("BTC") == Decimal("0.01")

    def test_get_min_loan_size_specific(self, lending_module):
        lending_module.min_loan_sizes = {"BTC": Decimal("0.1")}
        lending_module.min_loan_size = Decimal("0.01")
        assert lending_module.get_min_loan_size("BTC") == Decimal("0.1")
        assert lending_module.get_min_loan_size("ETH") == Decimal("0.01")

    def test_get_cur_spread(self, lending_module):
        lending_module.min_loan_size = Decimal("0.01")
        # Spread 10, Bal 1.0 -> 10 * 0.01 = 0.1 <= 1.0. Spread should be 10
        assert lending_module.get_cur_spread(10, Decimal("1.0"), "BTC") == 10

        # Spread 10, Bal 0.05. 10 * 0.01 = 0.1 > 0.05.
        # 5 * 0.01 = 0.05. Spread should be 5
        assert lending_module.get_cur_spread(10, Decimal("0.05"), "BTC") == 5

        # Spread 10, Bal 0.005. < 0.01. Spread should be 1 (min)
        assert lending_module.get_cur_spread(10, Decimal("0.005"), "BTC") == 1

    def test_get_gap_rate_basic(self, lending_module):
        # Order book: volumes: [1.0, 1.0, 1.0], rates: [0.01, 0.02, 0.03]
        order_book = {"volumes": ["1.0", "1.0", "1.0"], "rates": ["0.01", "0.02", "0.03"]}
        active_cur = "BTC"
        lending_module.loanOrdersRequestLimit[active_cur] = 10

        rate = lending_module.get_gap_rate(
            active_cur, Decimal("1.5"), order_book, Decimal("100"), raw=False
        )
        assert rate == Decimal("0.03")

    def test_get_gap_rate_raw(self, lending_module):
        order_book = {"volumes": ["1.0", "1.0", "1.0"], "rates": ["0.01", "0.02", "0.03"]}
        active_cur = "BTC"
        lending_module.loanOrdersRequestLimit[active_cur] = 10

        rate = lending_module.get_gap_rate(
            active_cur, Decimal("1.5"), order_book, Decimal("100"), raw=True
        )
        assert rate == Decimal("0.03")

    def test_get_gap_rate_max_limit(self, lending_module):
        # Reached end of order book
        order_book = {"volumes": ["1.0"], "rates": ["0.01"]}
        active_cur = "BTC"
        lending_module.loanOrdersRequestLimit[active_cur] = 10  # Limit not reached

        rate = lending_module.get_gap_rate(
            active_cur, Decimal("2.0"), order_book, Decimal("100"), raw=True
        )
        assert rate == lending_module.max_daily_rate

    def test_get_gap_rate_raises_stopiteration(self, lending_module):
        # Reached end of order book AND limit reached
        order_book = {"volumes": ["1.0"], "rates": ["0.01"]}
        active_cur = "BTC"
        lending_module.loanOrdersRequestLimit[active_cur] = 1  # Limit reached

        with pytest.raises(StopIteration):
            lending_module.get_gap_rate(
                active_cur, Decimal("2.0"), order_book, Decimal("100"), raw=True
            )

    def test_construct_orders_basic(self, lending_module):
        with patch.object(lending_module, "get_gap_mode_rates") as mock_gap_rates:
            mock_gap_rates.return_value = [Decimal("0.05"), Decimal("0.01")]
            lending_module.spread_lend = 5
            lending_module.min_loan_size = Decimal("0.01")

            resp = lending_module.construct_orders("BTC", Decimal("1.0"), Decimal("1.0"), None)

            assert len(resp["amounts"]) == 5
            assert len(resp["rates"]) == 5
            assert resp["rates"] == [
                Decimal("0.01"),
                Decimal("0.02"),
                Decimal("0.03"),
                Decimal("0.04"),
                Decimal("0.05"),
            ]
            assert resp["amounts"] == [
                Decimal("0.2"),
                Decimal("0.2"),
                Decimal("0.2"),
                Decimal("0.2"),
                Decimal("0.2"),
            ]

    def test_construct_orders_spread_1(self, lending_module):
        with patch.object(lending_module, "get_cur_spread") as mock_spread:
            mock_spread.return_value = 1
            resp = lending_module.construct_orders("BTC", Decimal("1.0"), Decimal("1.0"), None)

            assert len(resp["rates"]) == 1
            assert resp["rates"][0] == Decimal("0")
            assert resp["amounts"][0] == Decimal("1.0")

    def test_get_frr_or_min_daily_rate_basic(self, lending_module):
        lending_module.Config = Mock()
        lending_module.Config.get.return_value = "0.3"
        lending_module.Config.getboolean.return_value = False

        rate = lending_module.get_frr_or_min_daily_rate("BTC")
        assert rate == Decimal("0.003")

    def test_get_frr_or_min_daily_rate_bitfinex_frr(self, lending_module):
        lending_module.exchange = "BITFINEX"
        lending_module.Config = Mock()
        lending_module.Config.get.return_value = "0.1"
        lending_module.Config.getboolean.side_effect = lambda s, k, d: True if k == "frrasmin" else d
        lending_module.api = Mock()
        lending_module.api.get_frr.return_value = "0.002"

        lending_module.frrdelta_min = Decimal(0)
        lending_module.frrdelta_max = Decimal(0)

        rate = lending_module.get_frr_or_min_daily_rate("BTC")
        assert rate == Decimal("0.002")

    def test_get_min_daily_rate_coin_cfg(self, lending_module):
        lending_module.coin_cfg = {"BTC": {"minrate": "0.005", "frrasmin": False, "maxactive": 100}}
        with patch.object(lending_module, "get_frr_or_min_daily_rate") as mock_frr:
            mock_frr.return_value = Decimal("0.005")
            rate = lending_module.get_min_daily_rate("BTC")
            assert rate == Decimal("0.005")

    def test_get_min_daily_rate_disabled(self, lending_module):
        lending_module.coin_cfg = {"BTC": {"maxactive": 0, "minrate": "0.003", "frrasmin": False, "frrdelta_min": 0, "frrdelta_max": 0}}
        assert lending_module.get_min_daily_rate("BTC") is False

    def test_construct_order_books(self, lending_module):
        lending_module.api = Mock()
        lending_module.api.return_loan_orders.return_value = {
            "demands": [{"rate": "0.01", "amount": "10", "rangeMax": 2}],
            "offers": [{"rate": "0.02", "amount": "20", "rangeMax": 30}],
        }

        resps = lending_module.construct_order_books("BTC")
        assert len(resps) == 2
        assert resps[0]["rates"] == ["0.01"]
        assert resps[1]["rates"] == ["0.02"]

    def test_get_gap_mode_rates_relative(self, lending_module):
        with patch.object(lending_module, "construct_order_books") as mock_books:
            mock_books.return_value = [
                {},
                {"volumes": ["100", "100", "100", "100"], "rates": ["0.01", "0.02", "0.03", "0.04"]},
            ]
            lending_module.gap_mode_default = "relative"
            lending_module.gap_bottom_default = Decimal("50")
            lending_module.gap_top_default = Decimal("150")
            lending_module.loanOrdersRequestLimit = {"BTC": 10}

            rates = lending_module.get_gap_mode_rates("BTC", Decimal("100"), Decimal("100"), None)
            assert rates == [Decimal("0.03"), Decimal("0.02")]

    def test_create_lend_offer_dry_run(self, lending_module):
        lending_module.dry_run = True
        lending_module.api = Mock()
        lending_module.create_lend_offer("BTC", Decimal("1.0"), Decimal("0.01"), "2")
        lending_module.api.create_loan_offer.assert_not_called()

    def test_create_lend_offer_real(self, lending_module):
        lending_module.dry_run = False
        lending_module.api = Mock()
        lending_module.create_lend_offer("BTC", Decimal("1.0"), Decimal("0.01"), "2")
        # rate_f becomes 0.01 - 0.000001 = 0.009999
        args, _kwargs = lending_module.api.create_loan_offer.call_args
        assert args[0] == "BTC"
        assert args[1] == "1.00000000"
        assert args[2] == "2"
        assert args[3] == 0
        assert args[4] == pytest.approx(0.009999)

    def test_cancel_all_basic(self, lending_module):
        lending_module.api = Mock()
        lending_module.all_currencies = ["BTC"]
        lending_module.api.return_open_loan_offers.return_value = {
            "BTC": [{"id": 123, "amount": "1.0"}]
        }
        lending_module.api.return_available_account_balances.return_value = {
            "lending": {"BTC": "0.0"}
        }
        lending_module.min_loan_size = Decimal("0.01")
        lending_module.dry_run = False

        lending_module.cancel_all()
        lending_module.api.cancel_loan_offer.assert_called_with("BTC", 123)

    def test_lend_cur_basic(self, lending_module):
        lending_module.all_currencies = ["BTC"]
        lending_module.coin_cfg = {}
        lending_module.hide_coins = False
        lending_module.MaxToLend = Mock()
        # active_bal = 1.0
        lending_module.MaxToLend.amount_to_lend.return_value = Decimal("1.0")

        with patch.object(lending_module, "get_min_loan_size") as mock_min_size:
            mock_min_size.return_value = Decimal("0.01")
            with patch.object(lending_module, "construct_order_books") as mock_books:
                mock_books.return_value = [
                    {"rates": ["0.01"], "amount": ["10"], "rangeMax": [2]}, # demands
                    {"rates": ["0.02"], "volumes": ["20"], "rangeMax": [30]}, # offers
                ]
                with patch.object(lending_module, "get_min_daily_rate") as mock_min_rate:
                    mock_min_rate.return_value = Decimal("0.005")
                    with patch.object(lending_module, "construct_orders") as mock_orders:
                        mock_orders.return_value = {"amounts": [Decimal("1.0")], "rates": [Decimal("0.02")]}
                        with patch.object(lending_module, "create_lend_offer") as mock_create:
                            total_lent = {"BTC": Decimal("0")}
                            lending_balances = {"BTC": "1.0"}
                            res = lending_module.lend_cur("BTC", total_lent, lending_balances, None)
                            assert res == 1
                            mock_create.assert_called()

    def test_init_basic(self, lending_module):
        cfg = Mock()
        cfg.get_exchange.return_value = "POLONIEX"
        # Setup cfg.get to return sensible defaults for all calls
        cfg.get.side_effect = lambda s, k, d=None, min=None, max=None: d if d is not None else "0"
        cfg.get_gap_mode.return_value = "relative"
        cfg.get_coin_cfg.return_value = {}
        cfg.get_min_loan_sizes.return_value = {}
        cfg.get_currencies_list.return_value = []
        cfg.get_all_currencies.return_value = ["BTC"]
        cfg.getboolean.return_value = False
        notify_conf = {"notify_summary_minutes": 0, "notify_new_loans": False}
        lending_module.init(cfg, Mock(), MagicMock(), Mock(), Mock(), True, Mock(), notify_conf)
        assert lending_module.exchange == "POLONIEX"
        assert lending_module.dry_run is True

    def test_lend_all_basic(self, lending_module):
        lending_module.api = Mock()
        lending_module.api.return_available_account_balances.return_value = {"lending": {"BTC": "1.0"}}
        lending_module.all_currencies = ["BTC"]
        lending_module.gap_mode_default = "relative"
        lending_module.coin_cfg = {}
        lending_module.Data = Mock()
        lending_module.Data.get_total_lent.return_value = ({"BTC": Decimal("0")}, Decimal("0"))
        lending_module.MaxToLend = Mock()
        with patch.object(lending_module, "lend_cur") as mock_lend_cur:
            mock_lend_cur.return_value = 1
            lending_module.lend_all()
            mock_lend_cur.assert_called()
            assert lending_module.sleep_time == lending_module.sleep_time_active

    def test_notify_summary(self, lending_module):
        lending_module.log = MagicMock()
        lending_module.Data = Mock()
        lending_module.Data.get_total_lent.return_value = ({"BTC": Decimal("10")}, Decimal("0.1"))
        lending_module.Data.stringify_total_lent.return_value = "Summary"
        lending_module.scheduler = Mock()
        lending_module.notify_summary(60)
        lending_module.log.notify.assert_called_with("Summary", {})
        lending_module.scheduler.enter.assert_called_with(60, 1, lending_module.notify_summary, (60,))

    def test_notify_new_loans(self, lending_module):
        lending_module.api = Mock()
        lending_module.api.return_active_loans.return_value = {
            "provided": [{"id": 1, "currency": "BTC", "amount": "1.0", "rate": "0.01", "duration": 2}]
        }
        lending_module.loans_provided = []
        lending_module.log = MagicMock()
        lending_module.scheduler = Mock()
        lending_module.notify_new_loans(60)
        assert lending_module.loans_provided == lending_module.api.return_active_loans.return_value["provided"]
        lending_module.api.return_active_loans.return_value = {
            "provided": [
                {"id": 1, "currency": "BTC", "amount": "1.0", "rate": "0.01", "duration": 2},
                {"id": 2, "currency": "BTC", "amount": "2.0", "rate": "0.01", "duration": 2}
            ]
        }
        lending_module.notify_new_loans(60)
        lending_module.log.notify.assert_called()

    def test_transfer_balances(self, lending_module):
        lending_module.api = Mock()
        lending_module.api.return_balances.return_value = {"BTC": "1.0"}
        lending_module.transferable_currencies = ["BTC"]
        lending_module.log = MagicMock()
        lending_module.log.digestApiMsg.return_value = "Transfer Success"
        lending_module.transfer_balances()
        lending_module.api.transfer_balance.assert_called_with("BTC", "1.0", "exchange", "lending")
        lending_module.log.notify.assert_called_with("Transfer Success", {})

    def test_create_lend_offer_interpolation(self, lending_module):
        lending_module.dry_run = False
        lending_module.api = Mock()
        lending_module.xday_threshold = "0.05:25,0.07:120"
        lending_module.create_lend_offer("BTC", Decimal("1.0"), Decimal("0.0006"), "2")
        args, _kwargs = lending_module.api.create_loan_offer.call_args
        days = int(args[2])
        assert 25 < days < 120

    def test_create_lend_offer_end_date(self, lending_module):
        lending_module.Config = Mock()
        lending_module.Config.has_option.return_value = True
        lending_module.end_date = "2025-12-31"
        lending_module.Data = Mock()
        # Mock get_total_lent to return a tuple
        lending_module.Data.get_total_lent.return_value = ({"BTC": Decimal("0")}, Decimal("0"))
        # Only 1 day remaining
        lending_module.Data.get_max_duration.return_value = 1
        
        with pytest.raises(SystemExit):
            lending_module.create_lend_offer("BTC", Decimal("1.0"), Decimal("0.01"), "2")

    def test_lend_cur_below_min(self, lending_module):
        lending_module.all_currencies = ["BTC"]
        lending_module.hide_coins = True
        lending_module.MaxToLend = Mock()
        lending_module.MaxToLend.amount_to_lend.return_value = Decimal("1.0")
        
        with patch.object(lending_module, "get_min_loan_size") as mock_min_size:
            mock_min_size.return_value = Decimal("0.01")
            with patch.object(lending_module, "construct_order_books") as mock_books:
                mock_books.return_value = [{}, {"rates": ["0.001"], "volumes": ["20"]}]
                with patch.object(lending_module, "get_min_daily_rate") as mock_min_rate:
                    mock_min_rate.return_value = Decimal("0.005") # 0.001 < 0.005
                    with patch.object(lending_module, "construct_orders") as mock_orders:
                        mock_orders.return_value = {"amounts": [Decimal("1.0")], "rates": [Decimal("0.001")]}
                        
                        res = lending_module.lend_cur("BTC", {}, {"BTC": "1.0"}, None)
                        assert res == 0 # Should return 0 due to hide_coins and below min

    def test_lend_cur_min_amount_retry(self, lending_module):
        lending_module.all_currencies = ["BTC"]
        lending_module.hide_coins = False
        lending_module.MaxToLend = Mock()
        lending_module.MaxToLend.amount_to_lend.return_value = Decimal("1.0")
        lending_module.loanOrdersRequestLimit = {"BTC": 10}
        
        with patch.object(lending_module, "get_min_loan_size") as mock_min_size:
            mock_min_size.return_value = Decimal("0.01")
            with patch.object(lending_module, "construct_order_books") as mock_books:
                mock_books.return_value = [{}, {"rates": ["0.02"], "volumes": ["20"]}]
                with patch.object(lending_module, "get_min_daily_rate") as mock_min_rate:
                    mock_min_rate.return_value = Decimal("0.005")
                    with patch.object(lending_module, "construct_orders") as mock_orders:
                        mock_orders.return_value = {"amounts": [Decimal("1.0")], "rates": [Decimal("0.02")]}
                        with patch.object(lending_module, "create_lend_offer") as mock_create:
                            # First call raises amount error, second call (retry) succeeds
                            mock_create.side_effect = [Exception("Amount must be at least 0.05"), 1]
                            
                            res = lending_module.lend_cur("BTC", {}, {"BTC": "1.0"}, None)
                            assert res == 1
                            assert lending_module.min_loan_sizes["BTC"] == Decimal("0.05")

    def test_get_gap_mode_rates_rawbtc(self, lending_module):
        with patch.object(lending_module, "construct_order_books") as mock_books:
            mock_books.return_value = [
                {},
                {"volumes": ["100"], "rates": ["0.01"]},
            ]
            lending_module.gap_mode_default = "rawbtc"
            lending_module.gap_bottom_default = Decimal("10")
            lending_module.gap_top_default = Decimal("20")
            lending_module.loanOrdersRequestLimit = {"ETH": 10}
            
            ticker = {"BTC_ETH": {"last": "0.05"}}
            rates = lending_module.get_gap_mode_rates("ETH", Decimal("100"), Decimal("100"), ticker)
            assert rates == [lending_module.max_daily_rate, lending_module.max_daily_rate]

    def test_get_gap_mode_rates_coin_cfg(self, lending_module):
        lending_module.coin_cfg = {"BTC": {"gapmode": "raw", "gapbottom": 50, "gaptop": 150}}
        with patch.object(lending_module, "construct_order_books") as mock_books:
            mock_books.return_value = [
                {},
                {"volumes": ["100", "100", "100"], "rates": ["0.01", "0.02", "0.03"]},
            ]
            lending_module.loanOrdersRequestLimit = {"BTC": 10}
            rates = lending_module.get_gap_mode_rates("BTC", Decimal("100"), Decimal("100"), None)
            # bottom 50. i=1. rates[1]=0.02
            # top 150. i=2. rates[2]=0.03
            assert rates == [Decimal("0.03"), Decimal("0.02")]

    def test_get_min_daily_rate_analysis(self, lending_module):
        lending_module.Analysis = Mock()
        lending_module.currencies_to_analyse = ["BTC"]
        lending_module.analysis_method = "percentile"
        lending_module.Analysis.get_rate_suggestion.return_value = 0.008 # 0.8%
        
        # Base min rate 0.3%
        with patch.object(lending_module, "get_frr_or_min_daily_rate") as mock_frr:
            mock_frr.return_value = Decimal("0.003")
            rate = lending_module.get_min_daily_rate("BTC")
            assert rate == Decimal("0.003") # It doesn't overwrite yet, just logs.
            # Wait, looking at code: recommended_min is compared but cur_min_daily_rate NOT updated in current implementation?
            # recommended_min = Analysis.get_rate_suggestion(cur, method=analysis_method)
            # if cur_min_daily_rate < Decimal(str(recommended_min)) and log:
            #     log.log(...)
            # return Decimal(cur_min_daily_rate)
            # Yes, it doesn't update it. I'll just verify the call.
            lending_module.Analysis.get_rate_suggestion.assert_called_with("BTC", method="percentile")
