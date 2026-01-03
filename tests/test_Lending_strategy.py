"""
Tests for Lending Logic related to Strategy Selection
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from lendingbot.modules import Lending
from lendingbot.modules.Configuration import CoinConfig, LendingStrategy


@pytest.fixture(autouse=True)
def setup_lending():
    Lending._reset_globals()
    Lending.Data = MagicMock()
    Lending.Data.truncate.side_effect = lambda x, _: Decimal(x).quantize(Decimal("1.00000000"))


@pytest.fixture
def mock_coin_cfg_spread():
    return CoinConfig(
        minrate=Decimal("0.01"),
        maxactive=Decimal("100"),
        maxtolend=Decimal("1000"),
        maxpercenttolend=Decimal("0.5"),
        maxtolendrate=Decimal("0.05"),
        gapmode="raw",
        gapbottom=Decimal("10"),
        gaptop=Decimal("20"),
        lending_strategy=LendingStrategy.SPREAD,
        frrdelta_min=Decimal("0.0001"),
        frrdelta_max=Decimal("0.0005"),
    )


@pytest.fixture
def mock_coin_cfg_frr():
    return CoinConfig(
        minrate=Decimal("0.01"),
        maxactive=Decimal("100"),
        maxtolend=Decimal("1000"),
        maxpercenttolend=Decimal("0.5"),
        maxtolendrate=Decimal("0.05"),
        gapmode="raw",
        gapbottom=Decimal("10"),
        gaptop=Decimal("20"),
        lending_strategy=LendingStrategy.FRR,
        frrdelta_min=Decimal("0.0001"),
        frrdelta_max=Decimal("0.0005"),
    )


def test_construct_orders_spread_strategy(mock_coin_cfg_spread):
    """
    Test that Spread strategy uses the configured spread_lend value.
    """
    # Setup
    cur = "BTC"
    Lending.coin_cfg[cur] = mock_coin_cfg_spread
    Lending.spread_lend = 5  # Configured to split into 5 orders
    Lending.min_loan_sizes[cur] = Decimal("0.01")
    Lending.max_daily_rate = Decimal("5.0")  # High enough to allow all rates

    # Balance enough for 5 orders (0.01 * 5 = 0.05)
    cur_active_bal = Decimal("1.0")
    cur_total_bal = Decimal("1.0")

    # Mock construct_order_books/get_gap_mode_rates to return dummy rates
    with patch(
        "lendingbot.modules.Lending.get_gap_mode_rates",
        return_value=[Decimal("0.05"), Decimal("0.01")],
    ):
        orders = Lending.construct_orders(cur, cur_active_bal, cur_total_bal, None)

    # Verify
    assert len(orders["amounts"]) == 5
    assert len(orders["rates"]) == 5


def test_construct_orders_frr_strategy_forces_spread_1(mock_coin_cfg_frr):
    """
    Test that FRR strategy forces spread_lend to 1, regardless of global config.
    """
    # Setup
    cur = "BTC"
    Lending.coin_cfg[cur] = mock_coin_cfg_frr
    Lending.spread_lend = 5  # Configured to 5, but should be ignored/overridden to 1
    Lending.min_loan_sizes[cur] = Decimal("0.01")
    Lending.max_daily_rate = Decimal("5.0")

    cur_active_bal = Decimal("1.0")
    cur_total_bal = Decimal("1.0")

    # Mock construct_order_books/get_gap_mode_rates (should NOT be called if spread=1, but just in case)
    with patch(
        "lendingbot.modules.Lending.get_gap_mode_rates",
        return_value=[Decimal("0.05"), Decimal("0.01")],
    ) as mock_get_rates:
        orders = Lending.construct_orders(cur, cur_active_bal, cur_total_bal, None)

        # Verify
        assert len(orders["amounts"]) == 1
        assert len(orders["rates"]) == 1

        # If spread is 1, get_gap_mode_rates is skipped in construct_orders
        mock_get_rates.assert_not_called()
