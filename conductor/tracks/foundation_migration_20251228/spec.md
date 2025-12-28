# Track Specification - Core Python 3 Migration: Foundational Modules

## Overview
This track initiates the migration of the LendingBot codebase from Python 2.7 to Python 3.12+. It focuses on the foundational "low-dependency" modules: `Logger.py`, `ConsoleUtils.py`, and `Configuration.py`. The goal is to move these files to the modern `src/` layout, modernize their syntax, and enforce strict code quality standards.

## Functional Requirements
- **Library Modernization:** Update legacy Python 2 imports (e.g., `ConfigParser` -> `configparser`) to their Python 3 equivalents.
- **Syntax Migration:** Convert all `print` statements to functions, update exception handling, and handle String vs. Bytes where necessary.
- **Structural Migration:** Relocate files from `modules/` to `src/lendingbot/modules/`.
- **Refactoring:** Ensure `Configuration.py` and `Logger.py` work seamlessly in the new package structure.

## Non-Functional Requirements
- **Strict Quality Control:** Every migrated module must pass `uv run poe fix-full` (Ruff linting, formatting, and MyPy strict type checking).
- **Type Hinting:** Add PEP 484 type hints to all function signatures and class members.
- **Documentation:** Add Google-style docstrings to all public functions and classes.
- **Python 3.12+ Compatibility:** Ensure code leverages modern Python features where appropriate (e.g., `pathlib` for file operations).

## Acceptance Criteria
- [ ] Files `Logger.py`, `ConsoleUtils.py`, and `Configuration.py` exist in `src/lendingbot/modules/`.
- [ ] `uv run poe fix-full` passes with zero errors for these files.
- [ ] All existing tests related to these modules (in `tests/`) pass under Python 3.12.
- [ ] New `pytest` tests are added for any logic not covered by legacy tests.
- [ ] The bot can successfully initialize these modules when run via `uv run poe run-dev` (even if it fails later due to other unmigrated modules).

## Out of Scope
- Migration of Exchange APIs (`Bitfinex.py`, `Poloniex.py`).
- Migration of core lending logic (`Lending.py`).
- Migration of the WebServer.
