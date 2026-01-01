from typing import Any


def format_amount_currency(amount: Any, currency: str) -> str:
    """
    Formats a numerical value with its currency unit.

    - If currency is 'USD' or 'USDT', precision is set to 3 decimal places.
    - Otherwise, precision is set to 6 decimal places.
    - Trailing zeros and the decimal point are removed if not needed.

    Args:
        amount: The numerical value to format.
        currency: The currency unit (e.g., 'BTC', 'USD').

    Returns:
        A string in the format "XXX Currency".
    """
    from decimal import ROUND_HALF_UP, Decimal

    if amount is None:
        return f"0 {currency}"

    currency_upper = currency.upper()
    precision = 3 if currency_upper in ("USD", "USDT") else 6

    # Convert to Decimal for precise rounding
    # Use ROUND_HALF_UP to match common expectations (e.g., 0.0005 -> 0.001)
    d = Decimal(str(amount))
    rounded = d.quantize(Decimal(10) ** -precision, rounding=ROUND_HALF_UP)

    # Format and strip trailing zeros/dot
    formatted = f"{rounded:f}".rstrip("0").rstrip(".")

    # Handle the case where the amount might be essentially 0 after stripping
    if not formatted or formatted == "-0":
        formatted = "0"

    return f"{formatted} {currency}"


def format_rate_pct(rate: Any) -> str:
    """
    Formats a decimal rate as a percentage string.

    Args:
        rate: The decimal rate (e.g., 0.0001).

    Returns:
        A string in the format "X.XXXXX%".
    """
    precision = 5
    if rate is None:
        return f"{0:.{precision}f}%"
    return f"{float(rate) * 100:.{precision}f}%"
