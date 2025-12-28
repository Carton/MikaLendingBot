# Track Specification - English Documentation & ASCII Enforcement

## Overview
This track aims to internationalize the codebase by translating all remaining Chinese comments and docstrings into English. It also configures Ruff to prevent the introduction of new non-English documentation while maintaining flexibility for Unicode in user-facing strings.

## Functional Requirements
- **Comment Translation:** Translate all Chinese comments identified in modules like `Lending.py`, `WebServer.py`, and `__init__.py` to English, preserving their original intent and context.
- **Docstring Translation:** Ensure all docstrings are in English.
- **Ruff Configuration:** Update `pyproject.toml` to re-enable `RUF002` (ambiguous docstring characters) and `RUF003` (ambiguous comment characters).

## Non-Functional Requirements
- **Maintainability:** Ensure that future non-ASCII comments are flagged by the linter.
- **Consistency:** Use consistent English terminology throughout the technical notes.

## Acceptance Criteria
- [ ] No Chinese characters remain in comments or docstrings across the `src/` and `tests/` directories.
- [ ] `pyproject.toml` has `RUF002` and `RUF003` removed from the ignore list.
- [ ] `uv run poe fix-full` passes cleanly with the updated rules.

## Out of Scope
- Translating user-facing strings (handled by `RUF001`, which remains disabled for now).
- Redesigning the logic described in the TODOs.
