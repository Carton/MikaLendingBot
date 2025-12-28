# Plan: Coverage Improvement & Documentation Recovery

This plan targets the improvement of test coverage and documentation for critical legacy modules.

## Phase 1: MarketAnalysis Refactoring & Testing
Focus on `MarketAnalysis.py` which currently has 0% coverage and needs refactoring for testability.

- [x] Task: Analyze `src/lendingbot/modules/MarketAnalysis.py` to identify global dependencies and structure.
- [x] Task: Refactor `MarketAnalysis.py` to support dependency injection (pass api/config as arguments).
- [x] Task: Write comprehensive unit tests for `MarketAnalysis.py` targeting >80% coverage.
- [x] Task: Add Google-style docstrings to all public functions in `MarketAnalysis.py`.
- [x] Task: Quality Gate: Run `uv run poe check-full` and `uv run poe test-coverage` for this module.
- [x] Task: Conductor - User Manual Verification 'Phase 1: MarketAnalysis Refactoring & Testing' (Protocol in workflow.md) [checkpoint: Phase 1 complete]

## Phase 2: Lending Module Coverage & Documentation
Focus on `Lending.py`, the core logic module with low coverage.

- [x] Task: Analyze `src/lendingbot/modules/Lending.py` to identify untested paths (currently ~10% coverage).
- [x] Task: Supplement `tests/test_Lending.py` with tests for untested functions (e.g., `lend_all`, `cancel_all`, logic branches). Mock dependencies extensively.
- [x] Task: Add Google-style docstrings to any remaining public functions or complex logic in `Lending.py`.
- [x] Task: Quality Gate: Run `uv run poe check-full` and `uv run poe test-coverage` for this module.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Lending Module Coverage & Documentation' (Protocol in workflow.md) [checkpoint: Phase 2 complete]

## Phase 3: MaxToLend & Notify Coverage
Address the remaining lower-priority but important modules.

- [x] Task: Analyze `src/lendingbot/modules/MaxToLend.py` and `src/lendingbot/modules/Notify.py` for gaps.
- [x] Task: Write unit tests for `MaxToLend.py` targeting >80% coverage.
- [x] Task: Write unit tests for `Notify.py` targeting >80% coverage.
- [x] Task: Add Google-style docstrings to `MaxToLend.py` and `Notify.py`.
- [x] Task: Quality Gate: Run `uv run poe check-full` and verify project-wide coverage.
- [x] Task: Conductor - User Manual Verification 'Phase 3: MaxToLend & Notify Coverage' (Protocol in workflow.md) [checkpoint: Track complete]
