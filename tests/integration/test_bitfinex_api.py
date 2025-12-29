"""
Integration tests for Bitfinex API.

These tests make real API calls to Bitfinex and require valid API credentials.
"""

import threading
import time

import pytest

from lendingbot.modules.Bitfinex import Bitfinex


@pytest.mark.integration
@pytest.mark.slow
def test_multiple_calls(bitfinex_api: Bitfinex, start_time: float):
    """Test multiple concurrent API calls to Bitfinex.

    This test creates 10 concurrent threads that call return_open_loan_offers().
    It verifies that the API can handle concurrent requests properly.

    Args:
        bitfinex_api: Bitfinex API instance (from conftest.py fixture)
        start_time: Test start time for performance tracking
    """

    def call_get_open_loan_offers(thread_id: int):
        """Make an API call and log the timing.

        Args:
            thread_id: Thread identifier for logging
        """
        try:
            bitfinex_api.return_open_loan_offers()
            elapsed = time.time() - start_time
            print(f"Thread {thread_id} - API Call completed in {elapsed:.2f} sec")
        except Exception as e:
            print(f"Thread {thread_id} - Error: {e!s}")
            raise

    # Create and start 10 concurrent threads
    threads = []
    for i in range(10):
        thread = threading.Thread(target=call_get_open_loan_offers, args=(i + 1,))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    print("All concurrent API calls completed successfully")


# Note: The following test was commented out in the original Python 2.7 code.
# It can be uncommented and enhanced if needed for rate limiter testing.
#
# @pytest.mark.integration
# @pytest.mark.slow
# def test_rate_limiter(bitfinex_api: Bitfinex, start_time: float):
#     """Test API rate limiter.
#
#     Verifies that the (N % 6)th request is delayed by (N / 6) seconds.
#     Bitfinex rate limits requests to approximately 6 per second.
#
#     Args:
#         bitfinex_api: Bitfinex API instance
#         start_time: Test start time
#     """
#     def api_rate_limit(n: int, start: float):
#         """Test rate limit logic.
#
#         Args:
#             n: Request number
#             start: Start time for rate limit checking
#         """
#         bitfinex_api.limit_request_rate()
#
#         # Verify that the (N % 6)th request is delayed by (N / 6) sec from the start time
#         if n != 0 and n % 6 == 0:
#             elapsed = time.time() - start
#             print(f"Rate limit check for request {n}: {elapsed:.2f}s elapsed")
#             assert elapsed >= int(n / 6), f"Rate limit failed - expected {int(n / 6)}s delay"
#
#     # Create 20 threads to test rate limiting
#     threads = []
#     for i in range(20):
#         thread = threading.Thread(target=api_rate_limit, args=(i, start_time))
#         threads.append(thread)
#         thread.start()
#
#     # Wait for all threads to complete
#     for thread in threads:
#         thread.join()
