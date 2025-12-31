# Specification: Python 3 Modernization & Idiom Adoption

## Overview
This track aims to further modernize the `LendingBot_py3` codebase by moving beyond basic migration and adopting modern Python 3 (3.10+) idioms and best practices. The focus is on architectural improvements, data structure modernization, and replacing legacy standard library patterns with modern equivalents that automation tools miss.

## Goals
- Improve code readability, maintainability, and type safety through structural refactoring.
- Introduce `dataclasses` or `pydantic` for structured data modeling.
- Identify and replace legacy library usage and patterns (e.g., legacy `datetime` manipulations, inefficient collection usage, `io` handling) with modern, Pythonic alternatives.

## Scope

### Functional Requirements
- **Broad Pattern Scan:** Scan `src/` for logic patterns that can be simplified using Python 3.10+ features (beyond formatting).
- **Data Structure Refactoring:**
    - Identify classes or dictionary-based data structures (e.g., config objects, market data holders) that are better suited as `dataclasses` or `NamedTuples`.
    - Refactor these structures to improve type safety and self-documentation.
- **Library & Logic Modernization:**
    - Replace older standard library usage with modern equivalents (e.g., better context managers, modern `itertools`/`collections` usage).
    - Simplify complex logic blocks using newer Python syntax (e.g., `match` statements if applicable/useful, walrus operators `:=`).

### Non-Functional Requirements
- **No Functional Regressions:** The bot must maintain its current lending logic and exchange interactions.
- **Performance:** Modernization should not introduce performance bottlenecks.

## Acceptance Criteria
- [ ] At least one significant data structure (e.g., in `Data.py`, `Lending.py`, or `Configuration.py`) is refactored to use `dataclasses` or strongly typed structures.
- [ ] Legacy standard library patterns identified during the scan are updated to modern Python idioms.
- [ ] Codebase passes existing `pytest` suite without failures.
- [ ] Codebase passes `mypy` and `ruff` checks.

## Out of Scope
- Basic `pathlib` conversion and `f-string` formatting (covered by automated tooling).
- Complete rewrite of the networking layer (unless a specific legacy lib is identified for replacement).
- GUI/Web interface changes.
