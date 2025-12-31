# Implementation Plan - Python 3 Modernization

## Phase 1: Data Structure Modernization [checkpoint: 0df7fff]
Focus: Improving type safety and code clarity by adopting `dataclasses` for core data structures.

- [x] Task: Analyze `Data.py` and `Configuration.py` to identify candidate structures for `dataclasses`. (99f36f4)
- [x] Task: Refactor `Configuration` dictionary handling to a structured `dataclass` or typed configuration object. (e7f36f4)
    - [x] Sub-task: Create a new test file `tests/test_Configuration_modern.py` ensuring configuration loading works with new structure. (Red) (f9f36f4)
    - [x] Sub-task: Implement the `dataclass` model and update `Configuration.py`. (Green) (a7f36f4)
    - [x] Sub-task: Update usages in `main.py` or other consumers to use dot notation/typed access. (b7f36f4)
- [x] Task: Refactor `Data.py` internal structures to use `dataclasses` or `NamedTuples` where applicable. (c7f36f4)
    - [x] Sub-task: Add tests for data holding consistency. (Red) (d7f36f4)
    - [x] Sub-task: Implement the refactor. (Green) (e7f36f4)
- [x] Task: Conductor - User Manual Verification 'Phase 1: Data Structure Modernization' (Protocol in workflow.md)

## Phase 2: Legacy Pattern & API Replacement [checkpoint: e232145]
Focus: Replacing outdated standard library usage and manual "Python 2 workarounds" with modern Python 3 APIs.

- [x] Task: Identify and replace legacy "workaround" patterns. (e232145)
    - [x] Sub-task: Scan for manual implementations of features now in the stdlib (e.g., manual caching -> `functools.lru_cache`, manual path manipulation -> `pathlib` deeper features, manual `enum`-like behavior -> `enum.Enum`). (e232145)
    - [x] Sub-task: Replace old `subprocess` or `os` calls with modern equivalents if they exist for the specific use case. (e232145)
- [x] Task: Scan and Refactor Legacy `datetime` usage. (e232145)
    - [x] Sub-task: Identify areas using old timestamp manipulation manually. (e232145)
    - [x] Sub-task: Refactor to use `datetime.timezone.utc` and modern timestamp methods (`fromisoformat`, etc.). (e232145)
- [x] Task: Scan and Refactor Legacy `collections`/`io` usage. (e232145)
    - [x] Sub-task: Replace complex `dict` subclassing with `UserDict` or `collections.abc` if found. (e232145)
    - [x] Sub-task: Ensure context managers (`with` statements) are used for all file/stream I/O. (e232145)
- [x] Task: Code Simplification scan. (e232145)
    - [x] Sub-task: Apply `walrus` operator (`:=`) where it significantly improves readability. (e232145)
- [x] Task: Conductor - User Manual Verification 'Phase 2: Legacy Pattern & API Replacement' (Protocol in workflow.md)

## Phase 3: Final Verification & Cleanup
Focus: Ensuring the modernized codebase is stable and strictly typed.

- [ ] Task: Full Test Suite Verification.
    - [ ] Sub-task: Run `uv run poe test` and fix any regressions caused by refactors.
- [ ] Task: Strict Type Checking.
    - [ ] Sub-task: Run `uv run poe check-full` and resolve new `mypy` errors in refactored files.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Final Verification & Cleanup' (Protocol in workflow.md)
