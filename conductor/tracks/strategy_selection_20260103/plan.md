# Implementation Plan - Lending Strategy Selection

## Phase 1: Core Configuration and Logic Refactoring
- [x] Task: Remove `frrasmin` and implement `lending_strategy` in Configuration 52a829a
    - [ ] Sub-task: Create tests for new config validation (ensure FRR fails on non-Bitfinex).
    - [ ] Sub-task: Refactor `Configuration.py` to replace `frrasmin` with `lending_strategy`.
    - [ ] Sub-task: Implement validation logic to reject FRR strategy on unsupported exchanges.
- [ ] Task: Update Lending Logic for Strategy Enforcing
    - [ ] Sub-task: Create tests ensuring `spread_lend=1` is forced when Strategy is FRR.
    - [ ] Sub-task: Refactor `Lending.py` to branch logic based on `lending_strategy`.
    - [ ] Sub-task: Remove legacy `frrasmin` logic branches.
- [ ] Task: Conductor - User Manual Verification 'Core Configuration and Logic Refactoring' (Protocol in workflow.md)

## Phase 2: Web UI and API Updates
- [ ] Task: Expose Strategy via Web API
    - [ ] Sub-task: Update `WebServer.py` to include `lending_strategy` in the json output.
    - [ ] Sub-task: Verify API response includes the new field.
- [ ] Task: Update Frontend to React to Strategy
    - [ ] Sub-task: Modify `lendingbot.html` to group FRR/Spread controls.
    - [ ] Sub-task: Update `lendingbot.js` to hide/show groups based on `lending_strategy`.
- [ ] Task: Conductor - User Manual Verification 'Web UI and API Updates' (Protocol in workflow.md)

## Phase 3: Documentation and Final Cleanup
- [ ] Task: Update Configuration Documentation
    - [ ] Sub-task: Update `default.cfg.example` to feature `lending_strategy` and remove `frrasmin`.
    - [ ] Sub-task: Rewrite relevant sections in `docs/configuration.rst`.
- [ ] Task: Conductor - User Manual Verification 'Documentation and Final Cleanup' (Protocol in workflow.md)
