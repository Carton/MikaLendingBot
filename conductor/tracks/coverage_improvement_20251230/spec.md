# Specification - Systematic Coverage Improvement 20251230

## Overview
This track aims to systematically improve the test coverage of the LendingBot codebase, focusing on core logic modules first while maintaining the existing testing architecture. It includes a structured approach to identifying and addressing code testability issues through formal refactoring plans.

## Functional Requirements
- **Core Logic Prioritization**: Improve coverage in the following order:
    1. **High Priority (Core)**: `Lending.py`, `Data.py`, `MaxToLend.py`.
    2. **Secondary Priority**: `PluginsManager.py`, `ConsoleUtils.py`, `Poloniex.py`, `Logger.py`, `MarketAnalysis.py`, `Notify.py`.
    3. **Auxiliary/Low Priority**: `WebServer.py`, `AccountStats.py`, `Charts.py`.
- **Coverage Targets**:
    - Core modules: Achieve at least **80%** coverage.
    - Other modules: Achieve at least **60%** coverage (unless deemed extremely difficult to test).
- **Testability & Refactoring**:
    - If a module/function is difficult to test, a `refactor_plan.md` must be created.
    - Refactoring should prioritize dependency injection and function extraction to enable unit testing.
- **Architecture Adherence**: 
    - Use existing `pytest` structure.
    - Extend existing test files (e.g., `tests/test_Lending.py`) instead of creating redundant ones.
    - Use `unittest.mock` for external dependencies (APIs, File System, etc.).

## Non-Functional Requirements
- **Efficiency**: Avoid redundant or low-value test cases.
- **Stability**: Ensure no regressions are introduced during refactoring or test addition.
- **Documentation**: Refactoring plans must be clear and actionable.

## Acceptance Criteria
- [ ] Code coverage for `Lending.py`, `Data.py`, `MaxToLend.py` is >= 80%.
- [ ] Code coverage for other targeted modules is >= 60%.
- [ ] All existing and new tests pass successfully.
- [ ] Any required refactorings are documented in markdown plans before execution.
- [ ] No significant changes to the existing testing framework architecture.

## Out of Scope
- Rewriting the entire testing framework.
- Coverage improvement for modules already at 100% or those explicitly identified as "extremely difficult" after investigation.
