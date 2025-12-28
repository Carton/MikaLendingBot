"""
Tests for Bitfinex module core logic.
"""

from unittest.mock import MagicMock, patch

import pytest

from lendingbot.modules.Bitfinex import Bitfinex
from lendingbot.modules.ExchangeApi import ApiError


@pytest.fixture
def bitfinex_api():
    mock_config = MagicMock()

    def get_side_effect(section, key, default=None, min_val=None, max_val=None):
        if key == "timeout":
            return 30
        return "key"

    mock_config.get.side_effect = get_side_effect
    mock_config.getboolean.return_value = False
    mock_config.get_all_currencies.return_value = ["BTC"]
    mock_log = MagicMock()

    # Init calls return_available_account_balances, which we mock
    with patch(
        "lendingbot.modules.Bitfinex.Bitfinex.return_available_account_balances", return_value={}
    ):
        api = Bitfinex(mock_config, mock_log)
    return api


class TestBitfinexCore:
    def test_sign_payload(self, bitfinex_api):
        payload = {"request": "/v1/test", "nonce": "123"}
        signed = bitfinex_api._sign_payload(payload)

        assert "X-BFX-APIKEY" in signed
        assert "X-BFX-SIGNATURE" in signed
        assert "X-BFX-PAYLOAD" in signed

    @patch("requests.get")
    def test_get_request(self, mock_get, bitfinex_api):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"mid": "100"}]
        mock_get.return_value = mock_response

        ret = bitfinex_api._get("test")

        assert ret[0]["mid"] == "100"
        mock_get.assert_called_once()
        args, _ = mock_get.call_args
        assert "https://api.bitfinex.com/v1/test" in args[0]

    @patch("requests.post")
    def test_post_request(self, mock_post, bitfinex_api):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 1}
        mock_post.return_value = mock_response

        ret = bitfinex_api._post("test")

        assert ret["id"] == 1
        mock_post.assert_called_once()

    @patch("requests.get")
    def test_request_error_502(self, mock_get, bitfinex_api):
        mock_response = MagicMock()
        mock_response.status_code = 502
        mock_response.text = "Bad Gateway"
        mock_get.return_value = mock_response

        with pytest.raises(ApiError) as excinfo:
            bitfinex_api._get("test")

        assert "bad gateway" in str(excinfo.value)
