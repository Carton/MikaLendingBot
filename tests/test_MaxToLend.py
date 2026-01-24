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
                    # 1% -> 0.01
                    max_to_lend_rate=Decimal("1.0"),
                ),
            }
        )

        log = MagicMock()
        maxtolend_module.init(config, log)
        assert maxtolend_module.max_to_lend == Decimal("0")
        assert maxtolend_module.min_loan_size == Decimal("0.01")
        # test coin_cfg override
        assert maxtolend_module.coin_cfg["BTC"].max_to_lend == Decimal("1.0")
        assert maxtolend_module.coin_cfg["BTC"].max_to_lend_rate == Decimal("0.01")

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
                # 5% -> 0.05 internal
                max_to_lend_rate=Decimal("5.0"),
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

    # --- New tests for max_active_amount limit feature ---

    def test_max_active_amount_unlimited(self, maxtolend_module):
        """max_active_amount = -1 means no limit on total lending."""
        maxtolend_module.log = MagicMock()
        maxtolend_module.coin_cfg = {
            "USD": CoinConfig(
                max_active_amount=Decimal("-1"),  # Unlimited
            )
        }
        # total_lent = 5000, lending_balance = 3000. Should lend all 3000.
        res = maxtolend_module.amount_to_lend(
            Decimal("8000"), "USD", Decimal("3000"), Decimal("0.01"), total_lent=Decimal("5000")
        )
        assert res == Decimal("3000")

    def test_max_active_amount_limit_reached(self, maxtolend_module):
        """When total_lent >= max_active_amount, should return 0."""
        maxtolend_module.log = MagicMock()
        maxtolend_module.coin_cfg = {
            "USD": CoinConfig(
                max_active_amount=Decimal("5000"),  # Cap at 5000 USD
            )
        }
        # total_lent = 5000, which already equals the limit. Should lend 0.
        res = maxtolend_module.amount_to_lend(
            Decimal("8000"), "USD", Decimal("3000"), Decimal("0.01"), total_lent=Decimal("5000")
        )
        assert res == Decimal("0")
        # Verify log was called
        maxtolend_module.log.log.assert_called()

    def test_max_active_amount_partial_reduction(self, maxtolend_module):
        """When total_lent + lending_balance > max_active_amount, reduce lending amount."""
        maxtolend_module.log = MagicMock()
        maxtolend_module.coin_cfg = {
            "USD": CoinConfig(
                max_active_amount=Decimal("8000"),  # Cap at 8000 USD
            )
        }
        # total_lent = 5000, limit = 8000, so available_capacity = 3000.
        # lending_balance = 5000 > 3000, so should reduce to 3000.
        res = maxtolend_module.amount_to_lend(
            Decimal("10000"), "USD", Decimal("5000"), Decimal("0.01"), total_lent=Decimal("5000")
        )
        assert res == Decimal("3000")
        # Verify log was called
        maxtolend_module.log.log.assert_called()

    def test_max_active_amount_within_limit(self, maxtolend_module):
        """When total_lent + lending_balance <= max_active_amount, lend full amount."""
        maxtolend_module.log = MagicMock()
        maxtolend_module.coin_cfg = {
            "USD": CoinConfig(
                max_active_amount=Decimal("10000"),  # Cap at 10000 USD
            )
        }
        # total_lent = 3000, limit = 10000, available_capacity = 7000.
        # lending_balance = 2000 < 7000, so should lend all 2000.
        res = maxtolend_module.amount_to_lend(
            Decimal("5000"), "USD", Decimal("2000"), Decimal("0.01"), total_lent=Decimal("3000")
        )
        assert res == Decimal("2000")
