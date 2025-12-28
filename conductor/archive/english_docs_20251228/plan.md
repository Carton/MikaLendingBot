# Implementation Plan - English Documentation & ASCII Enforcement

This plan covers the translation of documentation and the configuration of linter rules to enforce English-only notes.

## Phase 1: Translation & Cleanup
Goal: Replace all Chinese text in the source code with English equivalents.

- [x] Task: Translate Chinese comment in `src/lendingbot/modules/Lending.py` regarding rate suggestions.
- [x] Task: Translate Chinese comments in `src/lendingbot/modules/WebServer.py` regarding data length and config updates.
- [x] Task: Translate Chinese comment in `src/lendingbot/modules/__init__.py` regarding folder purpose.
- [x] Task: Perform a final global search for any missed Chinese characters and translate them.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Translation & Cleanup' (Protocol in workflow.md)

## Phase 2: Linting Enforcement
Goal: Enable Ruff rules to maintain documentation standards.

- [x] Task: Update `pyproject.toml` to remove `RUF002` and `RUF003` from the ignore list.
- [x] Task: Run `uv run poe check-full` to verify that no non-ASCII documentation remains.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Linting Enforcement' (Protocol in workflow.md)
