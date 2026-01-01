from decimal import Decimal

from lendingbot.modules.Utils import format_amount_currency, format_rate_pct


def test_format_amount_currency():
    # Test USD/USDT (3 decimal places)
    assert format_amount_currency(1.2345, "USD") == "1.235 USD"
    assert format_amount_currency(1.2, "USD") == "1.2 USD"
    assert format_amount_currency(1.000, "USD") == "1 USD"
    assert format_amount_currency(1.2344, "USDT") == "1.234 USDT"

    # Test other currencies (6 decimal places)
    assert format_amount_currency(1.2345678, "BTC") == "1.234568 BTC"
    assert format_amount_currency(1.234, "ETH") == "1.234 ETH"
    assert format_amount_currency(1.0, "XMR") == "1 XMR"
    assert format_amount_currency(0.0000001, "BTC") == "0 BTC"  # rounded down to 0
    assert format_amount_currency(0.000001, "BTC") == "0.000001 BTC"

    # Test None
    assert format_amount_currency(None, "BTC") == "0 BTC"

    # Test Integer
    assert format_amount_currency(100, "USD") == "100 USD"

    # Test Decimal input
    assert format_amount_currency(Decimal("1.23456789"), "BTC") == "1.234568 BTC"


def test_format_rate_pct():
    # Test standard conversion
    assert format_rate_pct(0.0001) == "0.01000%"
    assert format_rate_pct(0.000123456) == "0.01235%"
    assert format_rate_pct(0) == "0.00000%"
    assert format_rate_pct(0.01) == "1.00000%"

    # Test None
    assert format_rate_pct(None) == "0.00000%"

    # Test Decimal input
    assert format_rate_pct(Decimal("0.0005")) == "0.05000%"
