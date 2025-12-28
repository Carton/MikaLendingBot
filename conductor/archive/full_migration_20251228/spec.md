# Track Specification - Full Python 3 Migration & Integration

## Overview
This track completes the migration of the LendingBot codebase to Python 3.12+. It covers all remaining modules (APIs, lending logic, web server), plugins, and the full test suite. The final goal is a fully functional, modernized bot running from the `src/` layout with a single entry point.

## Functional Requirements
- **Complete Module Migration:** Relocate all remaining files from `modules/` and `plugins/` to `src/lendingbot/modules/` and `src/lendingbot/plugins/`.
- **Logic Integration:** Move the core execution loop and logic from `lendingbot_legacy.py` into `src/lendingbot/main.py`.
- **API Layer Modernization:** Update `ExchangeApi`, `ExchangeApiFactory`, `Bitfinex`, and `Poloniex` to handle modern HTTP interactions and data types.
- **Web Server Migration:** Port `WebServer.py` to Python 3, ensuring compatibility with moved assets in `www/`.
- **Test Suite Standardisation:** Migrate all legacy tests to `pytest`, removing legacy import hacks and ensuring they run against the new package structure.

## Non-Functional Requirements
- **Zero-Exclusion Baseline:** Remove all migrated files from the `extend-exclude` list in `pyproject.toml`.
- **Strict Quality Control:** Every file must pass `uv run poe fix-full` (Ruff linting, formatting, and MyPy strict type checking).
- **Modern Standards:** Apply strict PEP 484 type hinting and Google-style docstrings throughout the codebase.
- **Resilient Pathing:** Use `pathlib` for all file and directory operations.

## Acceptance Criteria
- [ ] No files remain in the root `modules/` or `plugins/` directories.
- [ ] `src/lendingbot/main.py` is the fully functional entry point.
- [ ] The bot successfully executes a "Dry Run" loop via `uv run poe run-dev`.
- [ ] `uv run poe check-full` passes for the entire `src/` and `tests/` directories (excluding any remaining legacy files).
- [ ] All unit and integration tests pass under Python 3.12.

## Out of Scope
- Major architectural changes to the lending strategies themselves (beyond what's required for Py3 compatibility).
- UI/UX redesign of the legacy web dashboard.
