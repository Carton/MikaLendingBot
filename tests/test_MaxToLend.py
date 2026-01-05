"""
Tests for MaxToLend module using real Configuration models.
"""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from lendingbot.modules import MaxToLend
from lendingbot.modules.Configuration import CoinConfig, RootConfig


@pytest.fixture
def maxtolend_module():
    # Reset globals
    MaxToLend.max_to_lend = Decimal(0)
    MaxToLend.max_percent_to_lend = Decimal(0)
    MaxToLend.max_to_lend_rate = Decimal(0)
    MaxToLend.coin_cfg = {}
    MaxToLend.log = None
    MaxToLend.min_loan_size = Decimal("0.001")
    return MaxToLend


class TestMaxToLend:
    def test_maxtolend_init(self, maxtolend_module):
        config = RootConfig(
            coin={
                "default": CoinConfig(
                    max_to_lend=Decimal("0"),
                    max_percent_to_lend=Decimal("0"),
                    max_to_lend_rate=Decimal("0"),
                    min_loan_size=Decimal("0.01"),
                ),
                "BTC": CoinConfig(
                    max_to_lend=Decimal("1.0"),
                    max_percent_to_lend=Decimal("0.5"),
                    max_to_lend_rate=Decimal("0.01"),
                ),
            }
        )

        log = MagicMock()
        maxtolend_module.init(config, log)
        assert maxtolend_module.max_to_lend == Decimal("0")
        assert maxtolend_module.min_loan_size == Decimal("0.01")
        # test coin_cfg override
        assert maxtolend_module.coin_cfg["BTC"].max_to_lend == Decimal("1.0")

    def test_amount_to_lend_no_restriction(self, maxtolend_module):
        maxtolend_module.log = MagicMock()
        # Balance 10, low_rate 0.01. No restrictions set.
        res = maxtolend_module.amount_to_lend(Decimal("10"), "BTC", Decimal("10"), Decimal("0.01"))
        assert res == Decimal("10")

    def test_amount_to_lend_fixed_restriction(self, maxtolend_module):
        maxtolend_module.log = MagicMock()
        maxtolend_module.max_to_lend_rate = Decimal("0.02")  # restrict if market rate <= 2%
        maxtolend_module.max_to_lend = Decimal("5")  # only lend up to 5

        # Balance 10, low_rate 0.01 (restricted).
        # We want to lend until total lent is 5.
        # total_bal = 10, we want to keep 5. lending_balance is 10.
        # active_bal = 10 - (10 - 5) = 5.
        res = maxtolend_module.amount_to_lend(Decimal("10"), "BTC", Decimal("10"), Decimal("0.01"))
        assert res == Decimal("5")

    def test_amount_to_lend_percent_restriction(self, maxtolend_module):
        maxtolend_module.log = MagicMock()
        maxtolend_module.max_to_lend_rate = Decimal("0.02")
        maxtolend_module.max_percent_to_lend = Decimal("0.6")  # 60%

        # Balance 10, low_rate 0.01 (restricted).
        # 60% of 10 is 6.
        res = maxtolend_module.amount_to_lend(Decimal("10"), "BTC", Decimal("10"), Decimal("0.01"))
        assert res == Decimal("6")

    def test_amount_to_lend_min_size_cleanup(self, maxtolend_module):
        maxtolend_module.log = MagicMock()
        maxtolend_module.min_loan_size = Decimal("0.01")
        maxtolend_module.max_to_lend_rate = Decimal("0.02")
        maxtolend_module.max_to_lend = Decimal("9.995")

        # total_bal = 10, max_to_lend = 9.995.
        # restricted_amount = 10 - 9.995 = 0.005.
        # Since 0.005 < min_loan_size (0.01), it should lend all 10.
        res = maxtolend_module.amount_to_lend(Decimal("10"), "BTC", Decimal("10"), Decimal("0.01"))
        assert res == Decimal("10")

    def test_amount_to_lend_coin_cfg_override(self, maxtolend_module):
        maxtolend_module.log = MagicMock()
        maxtolend_module.coin_cfg = {
            "ETH": CoinConfig(
                max_to_lend=Decimal("2"),
                max_to_lend_rate=Decimal("0.05"),
            )
        }
        # Market rate 0.01 <= 0.05 (restricted for ETH)
        # total_bal=10, max_to_lend=2 -> lend 2.
        res = maxtolend_module.amount_to_lend(Decimal("10"), "ETH", Decimal("10"), Decimal("0.01"))
        assert res == Decimal("2")

    def test_amount_to_lend_no_restriction_due_to_rate(self, maxtolend_module):
        maxtolend_module.log = MagicMock()
        maxtolend_module.max_to_lend_rate = Decimal("0.01")  # Only restrict if rate <= 1%
        maxtolend_module.max_to_lend = Decimal("5")

        # Market rate 0.02 > 0.01. No restriction.
        res = maxtolend_module.amount_to_lend(Decimal("10"), "BTC", Decimal("10"), Decimal("0.02"))
        assert res == Decimal("10")
