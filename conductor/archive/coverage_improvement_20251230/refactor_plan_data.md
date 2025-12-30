# Refactoring Plan - Data.py

## Scope
- Module: `src/lendingbot/modules/Data.py`
- Primary functions: `init`, `get_on_order_balances`, `get_max_duration`, `get_total_lent`, `stringify_total_lent`, `update_conversion_rates`.

## Objectives
- Increase unit test coverage for `Data.py` from 31.93% to **>80%**.
- Mock external dependencies: Exchange API, Logger, Network (urllib), and Shell (subprocess).
- Avoid `SystemExit` in tests for `get_max_duration`.

## Approach
1.  **Dependency Injection**:
    - Allow passing `api` and `log` as optional arguments to functions to facilitate testing.
2.  **Mocking External Systems**:
    - Use `unittest.mock.patch` to intercept `urllib.request.urlopen` and `subprocess.check_output`.
3.  **Error Handling for Tests**:
    - Update `get_max_duration` to optionally raise an exception instead of `exit(1)` when in a testing context, or catch `SystemExit` in tests.
4.  **Utility Isolation**:
    - Test pure utilities like `truncate` and `timestamp` independently.

## Testing Strategy
1.  **Unit Tests**:
    - Test `get_max_duration` with various date formats and remaining days.
    - Test `truncate` with edge cases (scientific notation, different precision).
    - Test `timestamp` by mocking `datetime`.
2.  **Mocked Integration**:
    - Test `get_total_lent` and `get_on_order_balances` by mocking `api` responses.
    - Test `update_conversion_rates` by mocking `api.return_ticker` and `urllib.request.urlopen`.
3.  **Regression**:
    - Ensure all existing tests in `tests/test_Data.py` and `tests/test_Data_core.py` pass.
