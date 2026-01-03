# Implementation Plan - Lending Strategy Selection

## Phase 1: Core Configuration and Logic Refactoring [checkpoint: b7f4708]
- [x] Task: Remove `frrasmin` and implement `lending_strategy` in Configuration 52a829a
    - [x] Sub-task: Create tests for new config validation (ensure FRR fails on non-Bitfinex).
    - [x] Sub-task: Refactor `Configuration.py` to replace `frrasmin` with `lending_strategy`.
    - [x] Sub-task: Implement validation logic to reject FRR strategy on unsupported exchanges.
    - [x] Sub-task: Fix inheritance of `lending_strategy` from `[BOT]` section. b7f4708
- [x] Task: Update Lending Logic for Strategy Enforcing 3192ea4
    - [x] Sub-task: Create tests ensuring `spread_lend=1` is forced when Strategy is FRR.
    - [x] Sub-task: Refactor `Lending.py` to branch logic based on `lending_strategy`.
    - [x] Sub-task: Remove legacy `frrasmin` logic branches.
- [x] Task: Conductor - User Manual Verification 'Core Configuration and Logic Refactoring' (Protocol in workflow.md) 3fb4c0f

## Phase 2: Web UI and API Updates [checkpoint: 66f8969]
- [x] Task: Expose Strategy via Web API 66f8969
    - [x] Sub-task: Update `WebServer.py` to include `lending_strategy` in the json output.
    - [x] Sub-task: Verify API response includes the new field.
- [x] Task: Update Frontend to React to Strategy 66f8969
    - [x] Sub-task: Modify `lendingbot.html` to group FRR/Spread controls.
    - [x] Sub-task: Update `lendingbot.js` to hide/show groups based on `lending_strategy`.
- [x] Task: Conductor - User Manual Verification 'Web UI and API Updates' (Protocol in workflow.md) 66f8969

## Phase 3: Documentation and Final Cleanup
- [ ] Task: Update Configuration Documentation
    - [ ] Sub-task: Update `default.cfg.example` to feature `lending_strategy` and remove `frrasmin`.
    - [ ] Sub-task: Rewrite relevant sections in `docs/configuration.rst`.
- [ ] Task: Conductor - User Manual Verification 'Documentation and Final Cleanup' (Protocol in workflow.md)
