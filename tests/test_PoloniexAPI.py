import threading
import time
from unittest.mock import MagicMock

from lendingbot.modules.Poloniex import Poloniex


def test_rate_limiter() -> None:
    """Test rate limiter logic with mocks"""
    mock_config = MagicMock()
    mock_config.get.return_value = "30"
    mock_config.getboolean.return_value = False

    mock_log = MagicMock()

    api = Poloniex(mock_config, mock_log)

    start_time = time.time()

    def api_rate_limit(n: int, start: float) -> None:
        api.limit_request_rate()
        # verify that the (N % 6) th request is delayed by (N / 6) sec from the start time
        if n != 0 and n % 6 == 0:
            print(f"limit request {n} {start} {time.time()}\n")
            # In Py3, integer division is //, but the logic here might need adjustment
            # Original: assert time.time() - start >= int(n / 6)
            assert time.time() - start >= (n // 6)

    threads = []
    for i in range(20):
        t = threading.Thread(target=api_rate_limit, args=(i, start_time))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
