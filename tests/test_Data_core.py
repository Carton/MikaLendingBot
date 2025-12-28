"""
Tests for Data module core logic.
"""

from decimal import Decimal
from unittest.mock import MagicMock

from lendingbot.modules import Data


class TestDataCore:
    def test_stringify_total_lent(self):
        # Data.log needs to be mocked because stringify_total_lent calls log.updateStatusValue
        Data.log = MagicMock()

        total_lent = {"BTC": Decimal("1.0"), "ETH": Decimal("10.0")}
        rate_lent = {"BTC": Decimal("0.05"), "ETH": Decimal("0.2")}  # Rate sum: rate * amount

        # Average rate BTC: 0.05 / 1.0 = 0.05 = 5%
        # Average rate ETH: 0.2 / 10.0 = 0.02 = 2%

        result = Data.stringify_total_lent(total_lent, rate_lent)

        # Expected format: Lent: [1.0000 BTC @ 5.0000%] [10.0000 ETH @ 2.0000%]
        # Order is sorted by key
        assert "Lent:" in result
        assert "[1.0000 BTC @ 5.0000%]" in result
        assert "[10.0000 ETH @ 2.0000%]" in result

        # Check log updates
        Data.log.updateStatusValue.assert_any_call("BTC", "lentSum", Decimal("1.0"))
        Data.log.updateStatusValue.assert_any_call("BTC", "averageLendingRate", Decimal("5.0"))
        Data.log.updateStatusValue.assert_any_call("ETH", "lentSum", Decimal("10.0"))
        Data.log.updateStatusValue.assert_any_call("ETH", "averageLendingRate", Decimal("2.0"))
