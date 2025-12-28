# Specification: Coverage Improvement & Documentation Recovery

## Overview
This track focuses on addressing the uneven and low test coverage in several critical modules of the Mika Lending Bot. Simultaneously, it aims to improve code maintainability by adding comprehensive English docstrings (Google style) to important and complex functions within these modules.

## Functional Requirements
- **Improve Test Coverage:**
    - Increase unit test coverage to >80% for the following modules:
        - `src/lendingbot/modules/Lending.py`
        - `src/lendingbot/modules/MarketAnalysis.py`
        - `src/lendingbot/modules/MaxToLend.py`
        - `src/lendingbot/modules/Notify.py`
    - Focus on **Unit Testing** in isolation, mocking all external dependencies (API, Config, Logger, etc.).
- **Refactor for Testability (MarketAnalysis):**
    - For `MarketAnalysis.py` (currently 0% coverage), perform minor refactoring to enable better unit testing. This includes moving away from hardcoded globals towards dependency injection (e.g., passing the `api` and `config` objects to functions/classes).
- **Documentation Recovery:**
    - Add or improve **Google-style docstrings** for all public functions and complex internal logic in the targeted modules.
    - Ensure all comments and documentation are in **English**.

## Non-Functional Requirements
- **Consistency:** Maintain the code style and patterns established in the Python 3 migration.
- **Quality Gates:** All new tests must pass, and the code must pass `uv run poe check-full` (linting, type checking).

## Acceptance Criteria
- [ ] Unit test coverage for `Lending.py`, `MarketAnalysis.py`, `MaxToLend.py`, and `Notify.py` is at least 80%.
- [ ] All public functions in the targeted modules have complete Google-style docstrings.
- [ ] `MarketAnalysis.py` is refactored to support dependency injection for its core logic.
- [ ] No regressions in bot functionality are introduced.
- [ ] All tests pass using `uv run poe test`.
- [ ] The project passes `uv run poe check-full`.

## Out of Scope
- Implementation of new bot features or strategies.
- Refactoring modules other than those specified.
- Integration testing with live exchange APIs.
