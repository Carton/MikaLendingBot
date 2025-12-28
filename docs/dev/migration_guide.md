# Python 2.7 to 3.12+ Migration Guide: LendingBot

This guide outlines the strategy and practical steps for migrating the LendingBot codebase from Python 2.7 to modern Python (3.12+).

## 1. Migration Strategy

> [!IMPORTANT]
> **Recommended Workflow:** Use `python-modernize` first for bulk syntactic changes, then use **Antigravity (Code Agent)** for semantic and logic-heavy fixes.

### Tooling Strategy
- **Modernize/Futurize:** Excellent at handling "mechanical" changes like `print` statements, `long` to `int`, and `xrange` to `range`.
- **AI Agent (Antigravity):** Essential for handling complex issues:
    - **String vs. Bytes:** Python 3's strict separation.
    - **Dependency Resolution:** Finding modern equivalents for abandoned libraries.
    - **Type Hinting:** Adding PEP 484 type hints.

### Testing Strategy
1.  **Establish Baseline:** Run existing tests on Python 2.7 to identify pre-migration failures.
2.  **Cross-Version Testing:** Use `tox` to run tests against both Python 2.7 and Python 3.12+.
3.  **New Test Cases:** Focus on Unicode/Bytes handling and API responses.

---

## 2. Project Architecture

### New Directory Structure
The project is moving to a modern `src/` layout:

```
lendingbot/
├── src/
│   └── lendingbot/    # Main package
│       ├── __init__.py    # Package init
│       ├── main.py        # New Entry point
│       ├── modules/       # [TODO] Migrate from modules/
│       │   ├── Bitfinex.py
│       │   └── ...
│       └── plugins/       # [TODO] Migrate from plugins/
│           ├── AccountStats.py
│           └── ...
├── tests/                 # Existing tests
├── pyproject.toml         # Modern project configuration
├── main.py                # Legacy entry point (keep for ref)
└── lendingbot.py          # Legacy entry point (keep for ref)
```

---

## 3. Migration Steps

### Step 1: Update Imports
Map legacy Python 2 libraries to their Python 3 equivalents.

| Python 2.7 | Python 3 |
| :--- | :--- |
| `httplib` | `http.client` |
| `urllib2` | `urllib.request`, `urllib.error` |
| `SimpleHTTPServer` | `http.server` |
| `SocketServer` | `socketserver` |
| `ConfigParser` | `configparser` |

**Example:**
```python
# Old
import SimpleHTTPServer
from urllib2 import URLError

# New
import http.server
from urllib.error import URLError
```

### Step 2: Syntax Modernization

#### Print Function
```python
print 'Hello'      # Old
print('Hello')     # New
```

#### Integer Division
```python
result = 5 / 2     # Old (Result: 2)
result = 5 // 2    # New (Result: 2, explicit floor division)
result = 5 / 2     # New (Result: 2.5, float division)
```

#### String vs. Bytes
Python 3 strictly separates text and binary data.
```python
text = "Hello"                  # str (Unicode)
data = b"Hello"                 # bytes
decoded = data.decode('utf-8')  # bytes -> str
```

#### Iterators
Replace `xrange` with `range`.
```python
for i in range(100):  # 'xrange' is gone in Py3
    pass
```

### Step 3: Type Hinting
Add PEP 484 type hints to improve code quality and IDE support.

```python
from decimal import Decimal

def calculate_rate(amount: Decimal, rate: Decimal) -> Decimal:
    """Calculates the interest rate."""
    return amount * rate
```

### Step 4: WebServer Updates
The `SimpleHTTPRequestHandler` has moved.

```python
import http.server
import socketserver

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    # ...

# Server startup
socketserver.TCPServer.allow_reuse_address = True
server = socketserver.TCPServer((host, port), QuietHandler)
```

### Step 5: Exception Handling
```python
# Old
except Exception, e:

# New
except Exception as e:
```

---

## 4. Development Workflow

### Dependency Management
We use `uv` for fast package management.

```bash
# Install dependencies
uv sync --group dev --group test

# Add a runtime dependency
uv add requests

# Add a dev dependency
uv add --dev pytest
```

### Running the Application
```bash
# Run with default config
uv run python -m lendingbot.main

# Run using Poe task
uv run poe run
```

### Code Quality & Testing
```bash
# Full check (Format + Lint + Type Check)
uv run poe check-full

# Auto-fix issues
uv run poe fix-full

# Run tests
uv run poe test
```

---

## 5. Coding Standards

### Ruff Configuration
- **Line Length:** 100 characters
- **Target Version:** Python 3.12+
- **Import Sorting:** `isort` style

### Docstrings
Use Google style docstrings for all functions and classes.

```python
def example(arg1: int) -> bool:
    """
    Short description.

    Args:
        arg1: Description of arg1.

    Returns:
        True if successful, False otherwise.
    """
    return True
```

---

## 6. Migration Checklist

- [ ] Update imports (httplib -> http.client, etc.)
- [ ] Convert `print` statements to functions
- [ ] Update exception syntax (`as e`)
- [ ] Replace `xrange` with `range`
- [ ] Handle String vs. Bytes (encoding/decoding)
- [ ] Add Type Hints
- [ ] Add Docstrings
- [ ] Update file paths (use `pathlib`)
- [ ] Remove `# coding=utf-8` headers
- [ ] Run `uv run poe check-full`
- [ ] Fix/Update tests

### Recommended Order
1.  **Low Dependency:** `Logger.py`, `Data.py`, `RingBuffer.py`
2.  **Utils:** `Configuration.py`, `ConsoleUtils.py`
3.  **API:** `ExchangeApi.py`, `Bitfinex.py`, `Poloniex.py`
4.  **Logic:** `Lending.py`, `MarketAnalysis.py`
5.  **Web:** `WebServer.py`
6.  **Plugins:** `plugins/*`

---

## 7. FAQ

**Q: How to handle full-width Chinese punctuation warnings?**
A: `ruff` might flag characters like `，` or `：`. You can add `# noqa: RUF001` to the line to ignore it.

**Q: Old tests are failing with SyntaxErrors.**
A: Prioritize migrating the `src/` code first. Then fix tests one by one, or rewrite them using `pytest` fixtures.

**Q: CI/CD Setup?**
A: Use the provided `poe` tasks in GitHub Actions:
```yaml
- run: uv run poe check-full
- run: uv run poe test-coverage
```
