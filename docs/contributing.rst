Contributing
************

We welcome contributions! To ensure a smooth process, please follow these guidelines.

Code Quality and Styling
========================

We use automated tools to ensure code quality and consistent styling. To make following these standards as painless as possible, we use **Ruff** for linting and formatting.

Before submitting a Pull Request, please run the following command to check and fix any issues:

.. code-block:: bash

    uv run poe fix-full

This command will:
*   Format your code using Ruff.
*   Check for linting errors and apply auto-fixes.
*   Run **MyPy** for static type checking.

General Guidelines
------------------

*   **PEP8**: We follow standard PEP8 guidelines, which are largely enforced by our automated tooling.
*   **Line Length**: Limited to 100 characters.
*   **Type Hints**: We encourage the use of modern Python type hints (e.g., ``list[str]``, ``int | None``).
*   **Comments**: Only comment your code if you need to explain the *why* behind complex logic. Clear code is better than commented code.
*   **Variable Naming**: Follow PEP8 (``snake_case``). Avoid single-letter variables unless they are used in a very local, obvious context (like a loop index).

Configuration Options
=====================

New configuration options should be defined in the Pydantic models within the codebase.

*   Place new options near similar settings.
*   Provide clear descriptions and appropriate default values.
*   Ensure documentation in ``docs/configuration.rst`` is updated accordingly.

Building Documentation
======================

Documentation is built using **Sphinx**.

Building Locally
----------------

To build the documentation locally:

.. code-block:: bash

    uv run poe docs

The generated HTML will be available in ``docs/_build/html``. For a better developer experience, you can use the watch command to see changes in real-time:

.. code-block:: bash

    uv run poe docs-watch

CI/CD Deployment
----------------

The documentation is automatically built and deployed to GitHub Pages via GitHub Actions whenever changes are pushed to the ``master`` branch.

Writing Documentation
---------------------

*   Documentation is written in **reStructuredText** (RST).
*   Configurations should include a description, default value, and any specific constraints.
*   Follow the existing hierarchy and style of the documentation.
