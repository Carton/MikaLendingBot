"""
Tests for MaxToLend module.
"""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from lendingbot.modules import MaxToLend


@pytest.fixture
def mock_log():
    return MagicMock()


def test_maxtolend_init():
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
    MaxToLend.init(mock_config, log)
    assert MaxToLend.max_to_lend == Decimal("0")
    assert MaxToLend.coin_cfg["BTC"]["maxtolend"] == Decimal("1.0")


def test_amount_to_lend_no_restriction(mock_log):
    MaxToLend.log = mock_log
    MaxToLend.coin_cfg = {}
    MaxToLend.max_to_lend_rate = Decimal("0")  # No restriction
    MaxToLend.max_to_lend = Decimal("0")
    MaxToLend.max_percent_to_lend = Decimal("0")

    # Balance 10, low_rate 0.01.
    res = MaxToLend.amount_to_lend(Decimal("10"), "BTC", Decimal("10"), Decimal("0.01"))
    assert res == Decimal("10")


def test_amount_to_lend_fixed_restriction(mock_log):
    MaxToLend.log = mock_log
    MaxToLend.coin_cfg = {}
    MaxToLend.max_to_lend_rate = Decimal("0.02")  # restrict if market rate <= 2%
    MaxToLend.max_to_lend = Decimal("5")  # only lend up to 5

    # Balance 10, low_rate 0.01 (restricted).
    # Available bal 10. Max to lend 5.
    # Lending should be restricted to 5.
    res = MaxToLend.amount_to_lend(Decimal("10"), "BTC", Decimal("10"), Decimal("0.01"))
    assert res == Decimal("5")


def test_amount_to_lend_percent_restriction(mock_log):
    MaxToLend.log = mock_log
    MaxToLend.coin_cfg = {}
    MaxToLend.max_to_lend_rate = Decimal("0.02")
    MaxToLend.max_to_lend = Decimal("0")
    MaxToLend.max_percent_to_lend = Decimal("0.6")  # 60%

    # Balance 10, low_rate 0.01 (restricted).
    # 60% of 10 is 6.
    res = MaxToLend.amount_to_lend(Decimal("10"), "BTC", Decimal("10"), Decimal("0.01"))
    assert res == Decimal("6")


def test_amount_to_lend_min_size_cleanup(mock_log):
    MaxToLend.log = mock_log
    MaxToLend.min_loan_size = Decimal("0.01")
    MaxToLend.max_to_lend = Decimal("9.995")

    # 10 - 9.995 = 0.005 < 0.01. Should just lend all 10.
    res = MaxToLend.amount_to_lend(Decimal("10"), "BTC", Decimal("10"), Decimal("0.01"))
    assert res == Decimal("10")
