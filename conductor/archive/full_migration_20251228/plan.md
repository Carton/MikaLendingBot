# Implementation Plan - Full Python 3 Migration & Integration

This plan covers the final migration of all remaining modules, logic integration, and test suite modernization.

## Phase 1: Batch Relocation & Initial Conversion
Goal: Move all files to the new structure and apply automated syntactic fixes.

- [ ] Task: Move all files from `modules/` to `src/lendingbot/modules/` (excluding those already moved).
- [ ] Task: Move all files from `plugins/` to `src/lendingbot/plugins/`.
- [ ] Task: Remove all files from `extend-exclude` in `pyproject.toml` to enforce checking.
- [ ] Task: Apply automated upgrades across `src/lendingbot/` using `ruff check --select UP --fix`.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Batch Relocation & Initial Conversion' (Protocol in workflow.md)

## Phase 2: API & Data Layer Migration [checkpoint: api_data_migrated]
Goal: Modernize the foundation for exchange interactions.

- [x] Task: Migrate `Data.py`: Update logic and add strict type hints.
- [x] Task: Migrate `ExchangeApi.py` and `ExchangeApiFactory.py`: Port HTTP logic to Python 3.
- [x] Task: Migrate `Bitfinex.py` and `Poloniex.py`: Update API implementations.
- [x] Task: Migrate/Standardize tests for these modules in `tests/`.
- [x] Task: Conductor - User Manual Verification 'Phase 2: API & Data Layer Migration' (Protocol in workflow.md)

## Phase 3: Core Lending Logic & Plugins [checkpoint: core_logic_migrated]
Goal: Port the decision-making engine and extensibility layer.

- [x] Task: Migrate `Lending.py`, `MarketAnalysis.py`, and `MaxToLend.py`.
- [x] Task: Migrate all plugins in `src/lendingbot/plugins/`.
- [x] Task: Migrate/Standardize remaining logic tests in `tests/`.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Core Lending Logic & Plugins' (Protocol in workflow.md)

## Phase 4: Web Server & Final Integration
Goal: Port the web interface and unify the entry point.

- [~] Task: Migrate `WebServer.py`: Update `http.server` implementation.
- [ ] Task: Integrate remaining logic from `lendingbot_legacy.py` into `src/lendingbot/main.py`.
- [ ] Task: Verify full system functionality with `uv run poe run-dev`.
- [ ] Task: Final project-wide quality check with `uv run poe check-full`.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Web Server & Final Integration' (Protocol in workflow.md)
