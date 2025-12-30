# Implementation Plan - Systematic Coverage Improvement 20251230

## Phase 1: Environment & Baseline [checkpoint: aa61a61]
- [x] Task: Environment Verification & Baseline Report 75a79ca
    - [x] Sub-task: Verify `uv` and `poe` setup.
    - [x] Sub-task: Run full test suite to ensure current state is passing (`uv run poe test`).
    - [x] Sub-task: Generate initial coverage report (`uv run poe test-coverage`) and save as baseline.
- [x] Task: Conductor - User Manual Verification 'Environment & Baseline' (Protocol in workflow.md) aa61a61

## Phase 2: Core Logic - Lending.py (Target: >80%) [checkpoint: cb647ba]
- [x] Task: Analysis & Refactoring Plan for `Lending.py` ed5212a
    - [x] Sub-task: Analyze `Lending.py` for testability issues (global state, large functions).
    - [x] Sub-task: Draft `refactor_plan_lending.md` if significant refactoring is needed.
- [x] Task: Test Expansion - `Lending.py` Part 1 b642afe
    - [x] Sub-task: Create/Update `tests/test_Lending.py`.
    - [x] Sub-task: Add tests for critical paths (money handling, lending offers).
    - [x] Sub-task: Implement refactoring if planned.
    - [x] Sub-task: Verify coverage increase.
- [x] Task: Test Expansion - `Lending.py` Part 2 b642afe
    - [x] Sub-task: Add tests for edge cases and error handling.
    - [x] Sub-task: Finalize coverage for `Lending.py`.
- [x] Task: Conductor - User Manual Verification 'Core Logic - Lending.py' (Protocol in workflow.md) cb647ba

## Phase 3: Core Logic - Data.py & MaxToLend.py (Target: >80%) [checkpoint: 7d7c546]
- [x] Task: Analysis & Refactoring Plan for `Data.py` ae2ea85
    - [x] Sub-task: Analyze `Data.py` for dependencies (file I/O, API calls).
    - [x] Sub-task: Draft `refactor_plan_data.md` if needed.
- [x] Task: Test Expansion - `Data.py` 6ab3e9c
    - [x] Sub-task: Mock external data sources.
    - [x] Sub-task: Expand `tests/test_Data.py` to cover parsing and data management.
- [x] Task: Test Expansion - `MaxToLend.py` 6ab3e9c
    - [x] Sub-task: Analyze `MaxToLend.py` logic.
    - [x] Sub-task: Expand `tests/test_MaxToLend.py` to cover calculation logic.
- [x] Task: Conductor - User Manual Verification 'Core Logic - Data.py & MaxToLend.py' (Protocol in workflow.md) 7d7c546

## Phase 4: Secondary Modules (Target: >60%) [checkpoint: 646ea1a]
- [x] Task: Test Expansion - `PluginsManager.py` 646ea1a
    - [x] Sub-task: Add tests for plugin loading and lifecycle.
- [x] Task: Test Expansion - `ConsoleUtils.py` & `Logger.py` 646ea1a
    - [x] Sub-task: Add tests for console interaction and logging formatting.
- [x] Task: Test Expansion - `Poloniex.py` & `MarketAnalysis.py` 646ea1a
    - [x] Sub-task: Add mock-based tests for exchange interactions and analysis logic.
- [x] Task: Conductor - User Manual Verification 'Secondary Modules' (Protocol in workflow.md) 646ea1a

## Phase 5: Auxiliary Modules & Finalization (Target: >60%)
- [~] Task: Test Expansion - Auxiliary Modules
    - [ ] Sub-task: Attempt to improve `WebServer.py`, `AccountStats.py`, `Charts.py` coverage.
    - [ ] Sub-task: Document any unreachable/untestable code.
- [ ] Task: Final Verification
    - [ ] Sub-task: Run full regression suite.
    - [ ] Sub-task: Generate final coverage report.
    - [ ] Sub-task: Compare against baseline.
- [ ] Task: Conductor - User Manual Verification 'Auxiliary Modules & Finalization' (Protocol in workflow.md)
