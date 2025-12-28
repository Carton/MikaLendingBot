import threading
import time
from unittest.mock import MagicMock, patch

from lendingbot.modules.Bitfinex import Bitfinex


def test_multiple_calls() -> None:
    """Test fast api calls with mocks"""
    mock_config = MagicMock()
    mock_config.get.side_effect = (
        lambda _cat, opt, _default=None, *_args, **_kwargs: "30" if opt == "timeout" else "dummy"
    )
    mock_config.getboolean.return_value = False
    mock_config.get_all_currencies.return_value = ["BTC", "ETH"]

    mock_log = MagicMock()

    with patch.object(Bitfinex, "return_available_account_balances", return_value={}):
        api = Bitfinex(mock_config, mock_log)

    api.return_open_loan_offers = MagicMock(return_value={})  # type: ignore[method-assign]

    start_time = time.time()

    def call_get_open_loan_offers(i: int) -> None:
        api.return_open_loan_offers()
        print(f"API Call {i} sec: {time.time() - start_time}")

    threads = []
    for i in range(10):
        t = threading.Thread(target=call_get_open_loan_offers, args=(i + 1,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
