# Implementation Plan - Core Python 3 Migration: Foundational Modules

This plan covers the migration and structural update of `Logger.py`, `ConsoleUtils.py`, and `Configuration.py` to Python 3.12+.

## Phase 1: Structural Setup & Automated Conversion [checkpoint: 60dc5d7]
Goal: Relocate files and apply mechanical syntactic changes.

- [x] Task: Create target directory structure `src/lendingbot/modules/` and `src/lendingbot/plugins/` if they don't exist.
- [x] Task: Move `modules/Logger.py`, `modules/ConsoleUtils.py`, and `modules/Configuration.py` to `src/lendingbot/modules/`. f75215d
- [x] Task: Move `modules/__init__.py` (or create a new one) to `src/lendingbot/modules/__init__.py`. 6c1af55
- [x] Task: Apply automated syntax modernization using Ruff (e.g., `ruff check --select UP --fix`). 60dc5d7
- [x] Task: Conductor - User Manual Verification 'Phase 1: Structural Setup & Automated Conversion' (Protocol in workflow.md)

## Phase 2: Manual Migration & Refinement - Logger & ConsoleUtils [checkpoint: 13_passed]
Goal: Semantic fixes, type hints, and documentation for logging utilities.

- [x] Task: Migrate `Logger.py`: Update imports, fix String/Bytes issues, and add type hints.
- [x] Task: Migrate `ConsoleUtils.py`: Update imports and add type hints.
- [x] Task: Write tests for `Logger.py` and `ConsoleUtils.py` in `tests/`.
- [x] Task: Run `uv run poe fix-full` on `Logger.py` and `ConsoleUtils.py` until clean.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Manual Migration & Refinement - Logger & ConsoleUtils' (Protocol in workflow.md)

## Phase 3: Manual Migration & Refinement - Configuration [checkpoint: all_tests_passed]
Goal: Migrate the configuration parser and ensure it handles the project's config files correctly.

- [x] Task: Migrate `Configuration.py`: Update `configparser` usage and fix path handling using `pathlib`.
- [x] Task: Add strict type hints to `Configuration.py`.
- [x] Task: Migrate/Update existing tests for `Configuration.py`.
- [x] Task: Run `uv run poe fix-full` on `Configuration.py` until clean.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Manual Migration & Refinement - Configuration' (Protocol in workflow.md)

## Phase 4: Integration Verification [checkpoint: bot_init_success]
Goal: Ensure the migrated modules work together and provide a clean baseline.

- [x] Task: Create a minimal entry point in `src/lendingbot/main.py` that initializes Logger and Configuration.
- [x] Task: Verify successful initialization with `uv run poe run-dev`.
- [x] Task: Final full-project check with `uv run poe check-full`.
- [x] Task: Conductor - User Manual Verification 'Phase 4: Integration Verification' (Protocol in workflow.md)
