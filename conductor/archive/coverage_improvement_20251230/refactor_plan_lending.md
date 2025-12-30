# Refactoring Plan - Lending.py

## Scope
- Module: `src/lendingbot/modules/Lending.py`
- Primary functions: `init`, `lend_all`, `lend_cur`, `construct_orders`, `get_gap_mode_rates`, `create_lend_offer`.

## Objectives
- Increase unit test coverage for `Lending.py` from 29.17% to **>80%**.
- Reduce reliance on global state during testing.
- Enable easier mocking of the Exchange API and Logger.

## Approach
1.  **Dependency Injection (Lightweight)**:
    - While a full class-based refactor might be too disruptive, we will ensure that core logic functions can accept their dependencies as optional arguments, defaulting to the global variables if not provided.
    - Example: `def create_lend_offer(..., api_instance=None): api_instance = api_instance or api`.
2.  **Functional Extraction**:
    - Extract pure logic (e.g., rate calculations, amount splitting) from functions that have heavy side effects (API calls).
3.  **State Reset Mechanism**:
    - Implement a `_reset_globals()` function in `Lending.py` (for internal use by tests) to ensure a clean slate for each test case.
4.  **Mocking Strategy**:
    - Use `pytest` fixtures to provide mocked `api`, `log`, and `Config` objects.

## Testing Strategy
1.  **Unit Tests**:
    - Test `parse_xday_threshold` with various valid and invalid strings.
    - Test `get_cur_spread` with different balances and minimum loan sizes.
    - Test `construct_orders` with different gap modes and ticker data.
2.  **Integration (Mocked)**:
    - Test `lend_cur` by mocking `api.return_loan_orders` and verifying `api.create_loan_offer` calls.
    - Test `cancel_all` by mocking `api.return_open_loan_offers` and verifying `api.cancel_loan_offer` calls.
3.  **Regression**:
    - Ensure all existing tests in `tests/test_Lending.py` and `tests/test_Lending_core.py` pass.
