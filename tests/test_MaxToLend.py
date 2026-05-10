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
    MaxToLend.coin_cfg = {}
    MaxToLend.log = None
    MaxToLend.min_loan_size = Decimal("0.001")
    return MaxToLend


class TestMaxToLend:
    def test_maxtolend_init(self, maxtolend_module):
        config = RootConfig(
            coin={
                "default": CoinConfig(
                    min_loan_size=Decimal("0.01"),
                ),
                "BTC": CoinConfig(
                    max_active_amount=Decimal("1.0"),
                ),
            }
        )

        log = MagicMock()
        maxtolend_module.init(config, log)
        assert maxtolend_module.min_loan_size == Decimal("0.01")
        # test coin_cfg override
        assert maxtolend_module.coin_cfg["BTC"].max_active_amount == Decimal("1.0")

    # --- New tests for max_active_amount limit feature ---

    def test_max_active_amount_unlimited(self, maxtolend_module):
        """Omitting max_active_amount means no limit on total lending."""
        maxtolend_module.log = MagicMock()
        maxtolend_module.coin_cfg = {"USD": CoinConfig()}
        # total_lent = 5000, lending_balance = 3000. Should lend all 3000.
        res = maxtolend_module.amount_to_lend("USD", Decimal("3000"), total_lent=Decimal("5000"))
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
        res = maxtolend_module.amount_to_lend("USD", Decimal("3000"), total_lent=Decimal("5000"))
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
        res = maxtolend_module.amount_to_lend("USD", Decimal("5000"), total_lent=Decimal("5000"))
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
        res = maxtolend_module.amount_to_lend("USD", Decimal("2000"), total_lent=Decimal("3000"))
        assert res == Decimal("2000")
