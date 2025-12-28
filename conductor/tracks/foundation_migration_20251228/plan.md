# Implementation Plan - Core Python 3 Migration: Foundational Modules

This plan covers the migration and structural update of `Logger.py`, `ConsoleUtils.py`, and `Configuration.py` to Python 3.12+.

## Phase 1: Structural Setup & Automated Conversion [checkpoint: 60dc5d7]
Goal: Relocate files and apply mechanical syntactic changes.

- [x] Task: Create target directory structure `src/lendingbot/modules/` and `src/lendingbot/plugins/` if they don't exist.
- [x] Task: Move `modules/Logger.py`, `modules/ConsoleUtils.py`, and `modules/Configuration.py` to `src/lendingbot/modules/`. f75215d
- [x] Task: Move `modules/__init__.py` (or create a new one) to `src/lendingbot/modules/__init__.py`. 6c1af55
- [x] Task: Apply automated syntax modernization using Ruff (e.g., `ruff check --select UP --fix`). 60dc5d7
- [x] Task: Conductor - User Manual Verification 'Phase 1: Structural Setup & Automated Conversion' (Protocol in workflow.md)

## Phase 2: Manual Migration & Refinement - Logger & ConsoleUtils
Goal: Semantic fixes, type hints, and documentation for logging utilities.

- [ ] Task: Migrate `Logger.py`: Update imports, fix String/Bytes issues, and add type hints.
- [ ] Task: Migrate `ConsoleUtils.py`: Update imports and add type hints.
- [ ] Task: Write tests for `Logger.py` and `ConsoleUtils.py` in `tests/`.
- [ ] Task: Run `uv run poe fix-full` on `Logger.py` and `ConsoleUtils.py` until clean.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Manual Migration & Refinement - Logger & ConsoleUtils' (Protocol in workflow.md)

## Phase 3: Manual Migration & Refinement - Configuration
Goal: Migrate the configuration parser and ensure it handles the project's config files correctly.

- [ ] Task: Migrate `Configuration.py`: Update `configparser` usage and fix path handling using `pathlib`.
- [ ] Task: Add strict type hints to `Configuration.py`.
- [ ] Task: Migrate/Update existing tests for `Configuration.py`.
- [ ] Task: Run `uv run poe fix-full` on `Configuration.py` until clean.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Manual Migration & Refinement - Configuration' (Protocol in workflow.md)

## Phase 4: Integration Verification
Goal: Ensure the migrated modules work together and provide a clean baseline.

- [ ] Task: Create a minimal entry point in `src/lendingbot/main.py` that initializes Logger and Configuration.
- [ ] Task: Verify successful initialization with `uv run poe run-dev`.
- [ ] Task: Final full-project check with `uv run poe check-full`.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Integration Verification' (Protocol in workflow.md)
