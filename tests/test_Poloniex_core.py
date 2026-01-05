"""
Tests for Poloniex module core logic.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from lendingbot.modules.Poloniex import ApiError, Poloniex


from lendingbot.modules.Configuration import RootConfig, ApiConfig, BotConfig


@pytest.fixture
def poloniex_api():
    mock_config = RootConfig(
        api=ApiConfig(
            apikey="test_key",
            secret="test_secret"
        ),
        bot=BotConfig(
            request_timeout=30
        )
    )
    mock_log = MagicMock()
    return Poloniex(mock_config, mock_log)


class TestPoloniexCore:
    def test_api_query_public(self, poloniex_api):
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"BTC_ETH": {"last": "0.05"}}
            mock_get.return_value = mock_resp

            res = poloniex_api.return_ticker()
            assert res["BTC_ETH"]["last"] == "0.05"
            mock_get.assert_called()

    def test_api_query_private(self, poloniex_api):
        with patch("requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"result": "success"}
            mock_post.return_value = mock_resp

            # private query (not in public list)
            res = poloniex_api.return_balances()
            assert res["result"] == "success"

            # Verify it was called with headers (Sign/Key)
            _args, kwargs = mock_post.call_args
            headers = kwargs["headers"]
            assert "Key" in headers
            assert "Sign" in headers

    def test_api_error_handling(self, poloniex_api):
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"error": "Invalid API Key"}
            mock_get.return_value = mock_resp

            with pytest.raises(ApiError, match="Invalid API Key"):
                poloniex_api.return_ticker()

    def test_http_error_handling(self, poloniex_api):
        with patch("requests.get") as mock_get:
            # Construct a response with 429 error
            mock_resp = MagicMock()
            mock_resp.status_code = 429
            mock_resp.text = '{"error": "Rate limit exceeded"}'
            mock_resp.json.return_value = {"error": "Rate limit exceeded"}

            # Construct HTTPError that points to this response
            mock_error = requests.HTTPError(response=mock_resp)
            mock_get.side_effect = mock_error

            with pytest.raises(ApiError, match="Rate limit exceeded"):
                poloniex_api.return_ticker()

    def test_post_process(self):
        from lendingbot.modules.Poloniex import post_process

        data = {"return": [{"datetime": "2025-12-30 21:43:00"}]}
        res = post_process(data)
        assert "timestamp" in res["return"][0]
        assert isinstance(res["return"][0]["timestamp"], float)
