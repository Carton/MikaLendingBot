from decimal import Decimal

from lendingbot.modules import Data


def test_lent_data_dataclass():
    """
    Test that LentData is a dataclass and has expected fields.
    """
    from lendingbot.modules.Data import LentData

    total = {"BTC": Decimal("1.0")}
    rate = {"BTC": Decimal("0.0001")}
    ld = LentData(total_lent=total, rate_lent=rate)

    assert ld.total_lent["BTC"] == Decimal("1.0")
    assert ld.rate_lent["BTC"] == Decimal("0.0001")


def test_get_total_lent_returns_dataclass(monkeypatch):
    """
    Test that get_total_lent returns a LentData dataclass.
    """
    mock_api = type(
        "obj",
        (object,),
        {
            "return_active_loans": lambda: {
                "provided": [{"amount": "1.0", "rate": "0.0001", "currency": "BTC"}]
            }
        },
    )
    Data.api = mock_api

    ld = Data.get_total_lent()
    from lendingbot.modules.Data import LentData

    assert isinstance(ld, LentData)
    assert ld.total_lent["BTC"] == Decimal("1.0")
    assert ld.rate_lent["BTC"] == Decimal("0.0001")
