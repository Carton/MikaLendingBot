# Documentation Building

This directory contains the documentation for LendingBot. We use **Sphinx** to generate the documentation from reStructuredText (`.rst`) files.

## Prerequisites

Documentation dependencies are managed via `uv`. To install them:

```bash
uv sync --group docs
```

## Building Documentation

We use `poe` (Poe the Poet) to run documentation tasks. All commands should be run from the project root.

### Common Tasks

*   **Generate HTML**:
    ```bash
    uv run poe docs
    ```
    The output will be in `docs/_build/html/index.html`.

*   **Live Preview (Auto-reload)**:
    ```bash
    uv run poe docs-watch
    ```
    This starts a local server (usually at http://127.0.0.1:8000) that automatically rebuilds and refreshes the browser when you save changes to `.rst` files.

*   **Generate PDF**:
    ```bash
    uv run poe docs-pdf
    ```
    *Note: Requires a LaTeX distribution (like TeX Live or MiKTeX) installed on your system.*

*   **Clean Build Files**:
    ```bash
    uv run poe docs-clean
    ```

*   **Check Links**:
    ```bash
    uv run poe docs-linkcheck
    ```

## Writing Documentation

*   Documentation is written in [reStructuredText](https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html).
*   The main entry point is `index.rst`.
*   Configuration for Sphinx is in `conf.py`.
