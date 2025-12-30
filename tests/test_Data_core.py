"""
Tests for Data module core logic.
"""

import json
import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch, Mock

import pytest
from lendingbot.modules import Data


@pytest.fixture
def data_module():
    # Reset globals
    Data.api = None
    Data.log = None
    return Data


class TestDataCore:
    def test_stringify_total_lent(self, data_module):
        # Data.log needs to be mocked because stringify_total_lent calls log.updateStatusValue
        data_module.log = MagicMock()

        total_lent = {"BTC": Decimal("1.0"), "ETH": Decimal("10.0")}
        rate_lent = {"BTC": Decimal("0.05"), "ETH": Decimal("0.2")}  # Rate sum: rate * amount

        result = data_module.stringify_total_lent(total_lent, rate_lent)

        assert "Lent:" in result
        assert "[1.0000 BTC @ 5.0000%]" in result
        assert "[10.0000 ETH @ 2.0000%]" in result

        # Check log updates
        data_module.log.updateStatusValue.assert_any_call("BTC", "lentSum", Decimal("1.0"))
        data_module.log.updateStatusValue.assert_any_call("BTC", "averageLendingRate", Decimal("5.0"))

    def test_truncate(self, data_module):
        assert data_module.truncate(1.23456789, 4) == 1.2345
        assert data_module.truncate(Decimal("1.23456789"), 4) == 1.2345
        assert data_module.truncate(1.2, 4) == 1.2000
        assert data_module.truncate(123, 2) == 123.00
        # Scientific notation
        assert data_module.truncate(1.23e-5, 8) == 0.00001230

    def test_get_max_duration(self, data_module):
        # Use real dates to avoid mock hell
        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)
        end_date_str = f"{tomorrow.year},{tomorrow.month},{tomorrow.day}"
        
        assert data_module.get_max_duration(end_date_str, "order") == 1
        assert data_module.get_max_duration(end_date_str, "status") == " - Days Remaining: 1"
        
        # Test empty end_date
        assert data_module.get_max_duration("", "order") == ""

    def test_get_on_order_balances(self, data_module):
        data_module.api = Mock()
        data_module.api.return_open_loan_offers.return_value = {
            "BTC": [{"amount": "0.5"}, {"amount": "0.5"}],
            "ETH": [{"amount": "10.0"}]
        }
        balances = data_module.get_on_order_balances()
        assert balances["BTC"] == Decimal("1.0")
        assert balances["ETH"] == Decimal("10.0")

    def test_get_total_lent(self, data_module):
        data_module.api = Mock()
        data_module.api.return_active_loans.return_value = {
            "provided": [
                {"currency": "BTC", "amount": "1.0", "rate": "0.01"},
                {"currency": "BTC", "amount": "2.0", "rate": "0.02"}
            ]
        }
        total, rate = data_module.get_total_lent()
        assert total["BTC"] == Decimal("3.0")
        # 1.0*0.01 + 2.0*0.02 = 0.01 + 0.04 = 0.05
        assert rate["BTC"] == Decimal("0.05")

    def test_get_bot_version(self, data_module):
        with patch("subprocess.check_output") as mock_exec:
            mock_exec.return_value = b"1234\n"
            assert data_module.get_bot_version() == "1234"
            
            mock_exec.side_effect = Exception("error")
            assert data_module.get_bot_version() == "3.0.0"

    def test_update_conversion_rates_btc(self, data_module):
        data_module.log = MagicMock()
        data_module.api = Mock()
        # Mock get_total_lent internal call
        data_module.api.return_active_loans.return_value = {"provided": []}
        data_module.api.return_ticker.return_value = {}
        
        # Test default BTC
        data_module.update_conversion_rates("BTC", True)
        data_module.log.updateOutputCurrency.assert_any_call("currency", "BTC")

    def test_update_conversion_rates_alt(self, data_module):
        data_module.log = MagicMock()
        data_module.api = Mock()
        data_module.api.return_active_loans.return_value = {"provided": [{"currency": "ETH", "amount": "1", "rate": "0.01"}]}
        data_module.api.return_ticker.return_value = {
            "BTC_ETH": {"highestBid": "0.05"} # 1 ETH = 0.05 BTC
        }
        
        # ETH output currency
        data_module.update_conversion_rates("ETH", True)
        # 1 / 0.05 = 20
        data_module.log.updateOutputCurrency.assert_any_call("highestBid", 20.0)
        data_module.log.updateOutputCurrency.assert_any_call("currency", "ETH")

    def test_update_conversion_rates_external(self, data_module):
        data_module.log = MagicMock()
        data_module.api = Mock()
        data_module.api.return_active_loans.return_value = {"provided": []}
        data_module.api.return_ticker.return_value = {}
        
        with patch("urllib.request.urlopen") as mock_url:
            mock_response = MagicMock()
            mock_response.read.return_value = b"0.001" # 1 USD = 0.001 BTC (fake)
            mock_response.__enter__.return_value = mock_response
            mock_url.return_value = mock_response
            
            data_module.update_conversion_rates("USD", True)
            # 1 / 0.001 = 1000
            data_module.log.updateOutputCurrency.assert_any_call("highestBid", 1000.0)
            data_module.log.updateOutputCurrency.assert_any_call("currency", "USD")

    def test_get_lending_currencies(self, data_module):
        data_module.api = Mock()
        data_module.api.return_active_loans.return_value = {"provided": [{"currency": "BTC", "amount": "1", "rate": "0.01"}]}
        data_module.api.return_available_account_balances.return_value = {"lending": {"ETH": "1.0"}}
        
        currencies = data_module.get_lending_currencies()
        assert "BTC" in currencies
        assert "ETH" in currencies
        assert len(currencies) == 2

    def test_timestamp(self, data_module):
        ts = data_module.timestamp()
        # Format: 2025-12-30 21:43:00
        assert len(ts) == 19
        assert ts[4] == "-"
        assert ts[13] == ":"
