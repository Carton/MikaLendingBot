# Python 2.7 to 3.10+ Migration Guide: LendingBot

This guide outlines the strategy for migrating the LendingBot codebase from Python 2.7 to modern Python (3.10+).

## 1. Tooling Strategy: Automated + AI Agent

> [!IMPORTANT]
> **Recommended Workflow:** Use `python-modernize` first for bulk syntactic changes, then use **Antigravity (Code Agent)** for semantic and logic-heavy fixes.

### Why this approach?
- **Modernize/Futurize:** Excellent at handling "mechanical" changes like `print` statements, `long` to `int`, and `xrange` to `range`. It's faster and less prone to "hallucinations" for these basic syntax shifts.
- **AI Agent (Antigravity):** Essential for handling complex issues that rule-based tools miss:
    - **String vs. Bytes:** Python 3's strict separation. AI can infer if a variable should be `str` or `bytes` based on context (e.g., network data vs. UI labels).
    - **Dependency Resolution:** AI can research modern equivalents for abandoned libraries.
    - **Type Hinting:** AI can add PEP 484 type hints during migration to improve maintainability.

---

## 2. Testing & Verification Strategy

We must ensure "Functional Parity" before, during, and after migration.

### Step 1: Establish a Baseline (Pre-migration)
- **Current State:** The existing tests in `tests/` (e.g., `test_PoloniexAPI.py`) are sparse.
- **Action:** Run `pytest` on the Python 2.7 version. Any failing tests must be fixed *before* migration starts.
- **Improvement:** Expand unit tests for core logic (e.g., `Lending.py`, `Data.py`) to cover edge cases in Python 2 before moving.

### Step 2: Use Tox for Cross-Version Testing
- Create a `tox.ini` to run tests against both Python 2.7 and Python 3.10.
- Goal: Maintain a "dual-compatible" state if a "Big Bang" migration is too risky.

### Step 3: New Test Cases needed
- **Unicode/Bytes Testing:** Specifically test API responses and file I/O to ensure character encoding is handled correctly.
- **Async Verification:** If moving to `asyncio`, new tests will be needed for non-blocking I/O.

---

## 3. Python 3.10+ Native Adaptations

Don't just migrate syntax; modernize the architecture.

| Feature | Python 2.7 Pattern (Current) | Python 3.10+ Recommendation |
| :--- | :--- | :--- |
| **I/O** | `urllib2`, `httplib` | Use `httpx` or `aiohttp` for modern, possibly async, networking. |
| **Concurrency** | `threading` | Move to `asyncio` for the bot loop to handle multiple exchanges more efficiently. |
| **Logic** | Nested `if/elif` in `lendingbot.py` | Use **Structural Pattern Matching** (`match/case`) for API error handling. |
| **Data Classes** | Dictionary-heavy data | Use `@dataclass` for `Ticker`, `Balance`, and `LoanOrder` objects. |
| **Type Safety** | None | Add **Type Hints** throughout `modules/` for better IDE support and bug prevention. |
| **Config** | `ConfigParser` | Consider `pydantic` for robust configuration validation. |

---

## 4. Specific Code Patterns identified in LendingBot

- **Division:** Current code uses integer division (e.g., `int(n / 6)` in `test_PoloniexAPI.py`). In Python 3, `/` returns a float. Ensure `//` is used where integer division is intended.
- **Standard Library:** `urllib2` and `httplib` in `lendingbot.py:9-10` need careful replacement with `urllib.request` or better, `requests`/`httpx`.
- **Inheritance:** `ExchangeApi(object)` is redundant in Python 3; classes inherit from `object` by default.
- **Metaclasses:** `__metaclass__ = abc.ABCMeta` should become `class ExchangeApi(metaclass=abc.ABCMeta)`.

---

## Conclusion
Migration should be an iterative process. Start with the automated transformation, leverage the AI Agent for the "hard parts," and use a robust test suite to guarantee that the bot's lending logic remains safe and profitable.
