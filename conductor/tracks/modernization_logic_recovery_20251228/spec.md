# Specification: Python 3 Modernization & Logic Recovery

## Overview
This track focuses on the systematic migration and modernization of the legacy Python 2.7 codebase (located in `@old/`) to the new Python 3.12+ structure (located in `@src/`). The primary goal is to ensure that critical logic, features, and documentation (comments/docstrings) are not lost during the transition, while simultaneously applying modern coding standards.

## Functional Requirements
- **Logic Extraction & Modernization:**
    - Analyze legacy modules from `@old/` (starting with core logic like `Lending.py`, `Data.py` and Exchange APIs like `Poloniex.py`, `Bitfinex.py`).
    - Implement equivalent functionality in `@src/lendingbot/` using Python 3.12+ idioms.
    - Ensure all core features from the legacy version are functional in the new environment.
- **Comment & Documentation Recovery:**
    - Review legacy code for critical comments and docstrings.
    - Restore or adapt these comments into the new codebase. 
    - **Note:** Do not copy-paste obsolete comments; if the code has been refactored, ensure the new documentation accurately reflects the modernized logic (must be in English).
- **Correctness Verification:**
    - Use Test-Driven Development (TDD) to extract logic. Write Pytest unit tests in the new environment that define the expected behavior based on the legacy code before finalizing the implementation.

## Non-Functional Requirements
- **Code Quality:** Adhere to the project's tech stack (Ruff for linting, MyPy for strict type checking).
- **Maintainability:** Use Python 3.12+ features (type hints, `Path` for path operations, etc.) to improve code readability and maintainability.

## Acceptance Criteria
- [ ] Core modules (`Lending.py`, `Data.py`, `Poloniex.py`, `Bitfinex.py`) are fully migrated and modernized.
- [ ] No functional features from the legacy code are missing in the migrated versions.
- [ ] Critical documentation and docstrings are present and accurate in the new code.
- [ ] All new code passes the `uv run poe check-full` quality gate (linting, type checking).
- [ ] Unit tests cover the migrated logic with >80% coverage.

## Out of Scope
- Full migration of all modules in `@old/` in a single pass (this track focuses on core and API modules first).
- Introduction of entirely new features not present in the original codebase.
