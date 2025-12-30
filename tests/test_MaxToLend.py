"""
Tests for MaxToLend module.
"""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from lendingbot.modules import MaxToLend


@pytest.fixture
def maxtolend_module():
    # Reset globals
    MaxToLend.max_to_lend = Decimal(0)
    MaxToLend.max_percent_to_lend = Decimal(0)
    MaxToLend.max_to_lend_rate = Decimal(0)
    MaxToLend.coin_cfg = {}
    MaxToLend.log = None
    MaxToLend.min_loan_size = Decimal("0.01")
    return MaxToLend


class TestMaxToLend:
    def test_maxtolend_init(self, maxtolend_module):
        mock_config = MagicMock()
        mock_config.get_coin_cfg.return_value = {
            "BTC": {
                "maxtolend": Decimal("1.0"),
                "maxpercenttolend": Decimal("0.5"),
                "maxtolendrate": Decimal("0.01"),
            }
        }
        mock_config.get.return_value = "0"

        log = MagicMock()
        maxtolend_module.init(mock_config, log)
        assert maxtolend_module.max_to_lend == Decimal("0")
        assert maxtolend_module.coin_cfg["BTC"]["maxtolend"] == Decimal("1.0")

    def test_amount_to_lend_no_restriction(self, maxtolend_module):
        maxtolend_module.log = MagicMock()
        # Balance 10, low_rate 0.01.
        res = maxtolend_module.amount_to_lend(Decimal("10"), "BTC", Decimal("10"), Decimal("0.01"))
        assert res == Decimal("10")

    def test_amount_to_lend_fixed_restriction(self, maxtolend_module):
        maxtolend_module.log = MagicMock()
        maxtolend_module.max_to_lend_rate = Decimal("0.02")  # restrict if market rate <= 2%
        maxtolend_module.max_to_lend = Decimal("5")  # only lend up to 5

        # Balance 10, low_rate 0.01 (restricted).
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

        # 10 - 9.995 = 0.005 < 0.01. Should just lend all 10.
        res = maxtolend_module.amount_to_lend(Decimal("10"), "BTC", Decimal("10"), Decimal("0.01"))
        assert res == Decimal("10")

    def test_amount_to_lend_coin_cfg_override(self, maxtolend_module):
        maxtolend_module.log = MagicMock()
        maxtolend_module.coin_cfg = {
            "ETH": {
                "maxtolend": Decimal("2"),
                "maxpercenttolend": Decimal("0"),
                "maxtolendrate": Decimal("0.05"),
            }
        }
        # Market rate 0.01 <= 0.05 (restricted for ETH)
        res = maxtolend_module.amount_to_lend(Decimal("10"), "ETH", Decimal("10"), Decimal("0.01"))
        assert res == Decimal("2")

    def test_amount_to_lend_no_restriction_due_to_rate(self, maxtolend_module):
        maxtolend_module.log = MagicMock()
        maxtolend_module.max_to_lend_rate = Decimal("0.01")  # Only restrict if rate <= 1%
        maxtolend_module.max_to_lend = Decimal("5")

        # Market rate 0.02 > 0.01. No restriction.
        res = maxtolend_module.amount_to_lend(Decimal("10"), "BTC", Decimal("10"), Decimal("0.02"))
        assert res == Decimal("10")
