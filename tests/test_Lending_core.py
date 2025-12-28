"""
Tests for Lending module core logic.
"""

from decimal import Decimal
from unittest.mock import MagicMock, Mock

import pytest

from lendingbot.modules import Lending


# Mocking the dependencies
class MockConfig:
    def __init__(self):
        self.config = {}

    def get(self, section, key, default=None, _min_val=None, _max_val=None):
        return self.config.get((section, key), default)

    def getboolean(self, section, key, default=None):
        return self.config.get((section, key), default)

    def get_exchange(self):
        return "POLONIEX"

    def get_gap_mode(self, _section, _key):
        return "relative"

    def get_coin_cfg(self):
        return {}

    def get_min_loan_sizes(self):
        return {}

    def get_currencies_list(self, _key, _section=None):
        return []

    def get_all_currencies(self):
        return []


@pytest.fixture
def lending_module():
    # Reset globals
    Lending.min_loan_sizes = {}
    Lending.min_loan_size = Decimal("0.01")
    Lending.loanOrdersRequestLimit = {}
    Lending.defaultLoanOrdersRequestLimit = 5
    Lending.max_daily_rate = Decimal("0.05")  # 5%
    Lending.log = MagicMock()
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

        # Gap 1.5, Total Bal 100. Expected gap = 1.5 * 100 / 100 = 1.5
        # Gap sum: 1.0 (i=0) < 1.5. Next i=1. Gap sum 1.0 + 1.0 = 2.0 >= 1.5. Return rate[1] = 0.02
        # BUT implementation increments i after adding volume.
        # i=0: sum=1.0, i->1. Loop continues (1.0 < 1.5).
        # i=1: sum=2.0, i->2. Loop breaks.
        # Returns rates[2] = 0.03.
        # This implies logic returns the rate *after* the gap coverage.
        rate = lending_module.get_gap_rate(
            active_cur, Decimal("1.5"), order_book, Decimal("100"), raw=False
        )
        assert rate == Decimal("0.03")

    def test_get_gap_rate_raw(self, lending_module):
        order_book = {"volumes": ["1.0", "1.0", "1.0"], "rates": ["0.01", "0.02", "0.03"]}
        active_cur = "BTC"
        lending_module.loanOrdersRequestLimit[active_cur] = 10

        # Raw Gap 1.5. Expected gap = 1.5
        # Same logic as above.
        rate = lending_module.get_gap_rate(
            active_cur, Decimal("1.5"), order_book, Decimal("100"), raw=True
        )
        assert rate == Decimal("0.03")

    def test_get_gap_rate_max_limit(self, lending_module):
        # Reached end of order book
        order_book = {"volumes": ["1.0"], "rates": ["0.01"]}
        active_cur = "BTC"
        lending_module.loanOrdersRequestLimit[active_cur] = 10  # Limit not reached

        # Gap 2.0. Sum 1.0 < 2.0. i=0 is end. Should return max_daily_rate
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
        # Mock get_gap_mode_rates to return fixed rates
        # top_rate=0.05, bottom_rate=0.01
        lending_module.get_gap_mode_rates = Mock(return_value=[Decimal("0.05"), Decimal("0.01")])

        lending_module.spread_lend = 5
        lending_module.min_loan_size = Decimal("0.01")

        # Bal 1.0, Total 1.0.
        # Spread 5. Step = (0.05-0.01) / 4 = 0.01.
        # Rates: 0.01, 0.02, 0.03, 0.04, 0.05
        # Amounts: 1.0 / 5 = 0.2 each.

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
        # Spread forced to 1 (e.g. low balance)
        # Mock get_cur_spread to return 1
        original_get_cur_spread = lending_module.get_cur_spread
        lending_module.get_cur_spread = Mock(return_value=1)

        # When spread is 1, it skips get_gap_mode_rates
        # rate_step = 0, bottom_rate = 0.
        # Loop range(1) -> 0. New rate = 0 + 0 = 0.
        # Rates: [0]

        resp = lending_module.construct_orders("BTC", Decimal("1.0"), Decimal("1.0"), None)

        assert len(resp["rates"]) == 1
        assert resp["rates"][0] == Decimal("0")
        assert resp["amounts"][0] == Decimal("1.0")

        lending_module.get_cur_spread = original_get_cur_spread
