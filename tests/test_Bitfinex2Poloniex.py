import pytest

from lendingbot.modules.Bitfinex2Poloniex import Bitfinex2Poloniex


def test_convert_timestamp():
    # 1514764800 is 2018-01-01 00:00:00 UTC
    assert Bitfinex2Poloniex.convertTimestamp(1514764800) == "2018-01-01 00:00:00"
    assert Bitfinex2Poloniex.convertTimestamp("1514764800") == "2018-01-01 00:00:00"


def test_convert_open_loan_offers():
    bfx_offers = [
        {
            "id": 123,
            "currency": "BTC",
            "rate": "7.3",
            "remaining_amount": "1.0",
            "period": 2,
            "direction": "lend",
            "timestamp": "1514764800",
        },
        {
            "id": 124,
            "currency": "ETH",
            "rate": "14.6",
            "remaining_amount": "2.0",
            "period": 7,
            "direction": "lend",
            "timestamp": "1514764800",
        },
        {
            "id": 125,
            "currency": "BTC",
            "rate": "7.3",
            "remaining_amount": "0.0",  # should be skipped
            "period": 2,
            "direction": "lend",
            "timestamp": "1514764800",
        },
        {
            "id": 126,
            "currency": "BTC",
            "rate": "7.3",
            "remaining_amount": "1.0",
            "period": 2,
            "direction": "borrow",  # should be skipped
            "timestamp": "1514764800",
        },
    ]

    plx_offers = Bitfinex2Poloniex.convertOpenLoanOffers(bfx_offers)

    assert "BTC" in plx_offers
    assert "ETH" in plx_offers
    assert len(plx_offers["BTC"]) == 1
    assert len(plx_offers["ETH"]) == 1

    btc_offer = plx_offers["BTC"][0]
    assert btc_offer["id"] == 123
    assert float(btc_offer["rate"]) == pytest.approx(0.0002)
    assert btc_offer["amount"] == "1.0"
    assert btc_offer["duration"] == 2
    assert btc_offer["autoRenew"] == 0
    assert btc_offer["date"] == "2018-01-01 00:00:00"


def test_convert_active_loans():
    bfx_credits = [
        {
            "id": 456,
            "currency": "BTC",
            "rate": "7.3",
            "amount": "1.5",
            "period": 5,
            "timestamp": "1514764800",
        }
    ]

    plx_active = Bitfinex2Poloniex.convertActiveLoans(bfx_credits)

    assert "provided" in plx_active
    assert "used" in plx_active
    assert len(plx_active["provided"]) == 1
    assert len(plx_active["used"]) == 0

    loan = plx_active["provided"][0]
    assert loan["id"] == 456
    assert loan["currency"] == "BTC"
    assert float(loan["rate"]) == pytest.approx(0.0002)
    assert loan["amount"] == "1.5"
    assert loan["duration"] == 5
    assert loan["autoRenew"] == 0
    assert loan["date"] == "2018-01-01 00:00:00"


def test_convert_loan_orders():
    bfx_lendbook = {
        "bids": [{"rate": "7.3", "amount": "10.0", "period": 30}],
        "asks": [{"rate": "14.6", "amount": "20.0", "period": 2}],
    }

    plx_orders = Bitfinex2Poloniex.convertLoanOrders(bfx_lendbook)

    assert "demands" in plx_orders
    assert "offers" in plx_orders
    assert len(plx_orders["demands"]) == 1
    assert len(plx_orders["offers"]) == 1

    demand = plx_orders["demands"][0]
    assert demand["rate"] == "0.00020000"
    assert demand["amount"] == "10.0"
    assert demand["rangeMin"] == "2"
    assert int(demand["rangeMax"]) == 30

    offer = plx_orders["offers"][0]
    assert offer["rate"] == "0.00040000"
    assert offer["amount"] == "20.0"
    assert offer["rangeMin"] == "2"
    assert int(offer["rangeMax"]) == 2


def test_convert_account_balances():
    bfx_balances = [
        {"type": "deposit", "currency": "btc", "amount": "1.0", "available": "0.5"},
        {"type": "trading", "currency": "eth", "amount": "2.0", "available": "1.5"},
        {"type": "exchange", "currency": "usd", "amount": "100.0", "available": "90.0"},
        {"type": "conversion", "currency": "ltc", "amount": "1.0", "available": "1.0"},
        {
            "type": "deposit",
            "currency": "xrp",
            "amount": "0.0",  # should be skipped
            "available": "0.0",
        },
    ]

    # Test with account=""
    balances_all = Bitfinex2Poloniex.convertAccountBalances(bfx_balances)
    assert "lending" in balances_all
    assert "margin" in balances_all
    assert "exchange" in balances_all
    assert balances_all["lending"]["BTC"] == "0.5"
    assert balances_all["margin"]["ETH"] == "1.5"
    assert balances_all["exchange"]["USD"] == "90.0"
    assert "LTC" not in balances_all["lending"]  # conversion skipped
    assert "XRP" not in balances_all["lending"]  # amount 0 skipped

    # Test with account="lending"
    balances_lending = Bitfinex2Poloniex.convertAccountBalances(bfx_balances, "lending")
    assert "lending" in balances_lending
    assert "margin" not in balances_lending
    assert balances_lending["lending"]["BTC"] == "0.5"
    assert "ETH" not in balances_lending["lending"]

    # Test with account="margin"
    balances_margin = Bitfinex2Poloniex.convertAccountBalances(bfx_balances, "margin")
    assert "margin" in balances_margin
    assert "lending" not in balances_margin
    assert balances_margin["margin"]["ETH"] == "1.5"
