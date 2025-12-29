"""
Integration tests for Poloniex API.

These tests make real API calls to Poloniex and require valid API credentials.
"""

import threading
import time

import pytest

from lendingbot.modules.Poloniex import Poloniex


@pytest.mark.integration
@pytest.mark.slow
def test_rate_limiter(poloniex_api: Poloniex, start_time: float):
    """Test API rate limiter for Poloniex.

    This test creates 20 concurrent threads that call limit_request_rate().
    It verifies that the rate limiter properly delays requests.
    Poloniex rate limits requests to approximately 6 per second.

    The test verifies that the (N % 6)th request is delayed by (N / 6) seconds
    from the start time.

    Args:
        poloniex_api: Poloniex API instance (from conftest.py fixture)
        start_time: Test start time for rate limit verification
    """
    def api_rate_limit(n: int, start: float):
        """Test rate limit logic.

        Args:
            n: Request number
            start: Start time for rate limit checking
        """
        poloniex_api.limit_request_rate()

        # Verify that the (N % 6)th request is delayed by (N / 6) sec from the start time
        if n != 0 and n % 6 == 0:
            elapsed = time.time() - start
            expected_delay = int(n / 6)
            print(f"Rate limit check for request {n}: {elapsed:.2f}s elapsed " +
                  f"(started at {start:.2f}, expected >= {expected_delay}s)")
            assert elapsed >= expected_delay, \
                f"Rate limit failed - expected at least {expected_delay}s delay, got {elapsed:.2f}s"

    # Create and start 20 threads to test rate limiting
    threads = []
    for i in range(20):
        thread = threading.Thread(target=api_rate_limit, args=(i, start_time))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    print("All rate limit tests completed successfully")


# Note: The following test was commented out in the original Python 2.7 code.
# It can be uncommented and enhanced if needed for testing multiple concurrent API calls.
#
# @pytest.mark.integration
# @pytest.mark.slow
# def test_multiple_calls(poloniex_api: Poloniex):
#     """Test multiple concurrent API calls to Poloniex.
#
#     This test creates 9 concurrent threads that call return_open_loan_offers().
#
#     Args:
#         poloniex_api: Poloniex API instance
#     """
#     def call_return_open_loan_offers(query_id: int):
#         """Make an API call and log the result.
#
#         Args:
#             query_id: Query identifier for logging
#         """
#         try:
#             result = poloniex_api.return_open_loan_offers()
#             print(f"API Query {query_id} completed")
#         except Exception as e:
#             print(f"API Query {query_id} - Error: {str(e)}")
#             raise
#
#     # Create and start 9 concurrent threads
#     threads = []
#     for i in range(9):
#         thread = threading.Thread(target=call_return_open_loan_offers, args=(i + 1,))
#         threads.append(thread)
#         thread.start()
#
#     # Wait for all threads to complete
#     for thread in threads:
#         thread.join()
#
#     print("All concurrent API calls completed successfully")
