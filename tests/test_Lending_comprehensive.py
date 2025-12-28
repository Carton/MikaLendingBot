"""
Final robust tests for Lending module.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from lendingbot.modules import Lending


@pytest.fixture(autouse=True)
def setup_lending_globals():
    """Ensure all global dependencies are mocked before each test."""
    Lending.api = MagicMock()
    Lending.log = MagicMock()
    Lending.Data = MagicMock()
    Lending.MaxToLend = MagicMock()
    Lending.Config = MagicMock()

    # Setup some basic state
    Lending.min_loan_sizes = {}
    Lending.min_loan_size = Decimal("0.01")
    Lending.all_currencies = ["BTC"]
    Lending.hide_coins = False
    Lending.compete_rate = 0.00064
    Lending.notify_conf = {"notify_summary_minutes": 0, "notify_new_loans": False}
    yield


def test_get_min_loan_size_basic():
    Lending.min_loan_sizes = {"BTC": Decimal("0.05")}
    assert Lending.get_min_loan_size("BTC") == Decimal("0.05")
    assert Lending.get_min_loan_size("ETH") == Decimal("0.01")


def test_lend_cur_minimal():
    # Setup mocks to pass all guards and reach the creation part
    Lending.MaxToLend.amount_to_lend.return_value = Decimal("1.0")
    order_book = {"rates": ["0.01"], "volumes": ["1.0"]}
    Lending.min_loan_size = Decimal("0.01")
    Lending.hide_coins = False

    with (
        patch.object(Lending, "construct_order_books", return_value=[None, order_book]),
        patch.object(Lending, "get_min_daily_rate", return_value=Decimal("0.001")),
        patch.object(
            Lending, "construct_orders", return_value={"amounts": [Decimal("1.0")], "rates": [0.01]}
        ),
        patch.object(Lending, "create_lend_offer") as mock_create,
    ):
        res = Lending.lend_cur("BTC", {}, {"BTC": "1.0"}, None)
        print(f"DEBUG: res={res}, min_size={Lending.get_min_loan_size('BTC')}")
        assert res == 1
        assert mock_create.called


def test_notify_summary_minimal():
    Lending.Data.get_total_lent.return_value = ({}, {})
    Lending.Data.stringify_total_lent.return_value = "Status"
    Lending.scheduler = MagicMock()

    Lending.notify_summary(60)
    assert Lending.log.notify.called


def test_notify_new_loans_minimal():
    Lending.api.return_active_loans.return_value = {"provided": []}
    Lending.scheduler = MagicMock()

    Lending.notify_new_loans(60)
    assert Lending.api.return_active_loans.called
