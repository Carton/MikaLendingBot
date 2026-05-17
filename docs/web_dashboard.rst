Web Dashboard Architecture
**************************

The web dashboard is now a React application served by the bot's built-in
FastAPI server. The source code lives under ``frontend/`` and the production
assets are built into ``www/``.

Runtime Stack
=============

Backend
-------

The Python bot starts ``src/lendingbot/modules/WebServer.py`` when
``[bot.web].enabled`` is true. The server uses:

* **FastAPI** for HTTP API routes.
* **Uvicorn** to run the ASGI app in a daemon thread beside the lending loop.
* **Server-Sent Events (SSE)** for streaming new log lines to the browser.
* **StaticFiles** to serve the compiled files in the configured web template
  directory, usually ``www``.

Frontend
--------

The dashboard frontend uses:

* **React** and **TypeScript** for UI state and components.
* **Vite** for production builds.
* **Ant Design** for layout and controls.
* **ECharts** for profit charts.
* Local bundled assets under ``www/assets``. The dashboard no longer depends on
  CDN-hosted jQuery, Bootstrap, or Google Charts.

Pages and Build Output
======================

The Vite build writes these entry pages and assets:

* ``www/lendingbot.html`` for the main dashboard.
* ``www/charts.html`` for profit charts.
* ``www/index.html`` which redirects to the dashboard.
* ``www/assets/main.js`` and ``www/assets/main.css`` for the main app bundle.
* Split chart/vendor bundles such as ``ChartsPage.js``, ``antd.js``, and
  ``charts2.js``.

The web server uses the files in ``www/`` at runtime. If you modify files under
``frontend/``, run:

.. code-block:: bash

    npm run build

This compiles TypeScript, runs Vite, and refreshes the generated ``www`` assets.
After backend API changes, restart ``uv run lendingbot`` so the FastAPI routes
are reloaded. Pure frontend asset changes can usually be picked up with a browser
refresh after rebuilding.

Dashboard Data Flow
===================

The React dashboard uses a small number of consolidated endpoints:

* ``GET /api/dashboard/state`` returns the initial dashboard state, including
  settings, bot status, persisted stats, plugin metadata, lending strategy
  names, pause state, and a recent log snapshot.
* ``GET /api/dashboard/state?include_logs=false`` returns the same dashboard
  state without ``recent_logs``. The frontend uses this for scheduled polling
  and post-action refreshes to avoid repeatedly transferring the same log data.
* ``GET /stream-logs`` keeps an SSE connection open and pushes new log lines as
  they are written.
* ``GET /api/charts/history`` returns the chart JSON dumped by the Charts
  plugin.
* ``POST /api/settings`` saves backend web settings such as refresh interval,
  output currency display mode, and FRR adjustment range.
* ``POST /api/lending/pause`` and ``POST /api/lending/resume`` update the live
  lending pause state.

On initial load, the dashboard fetches ``/api/dashboard/state`` once so it can
show the current recent log snapshot. After that, log updates come from
``/stream-logs``. Regular dashboard polling uses ``include_logs=false`` and keeps
the logs already held in the browser.

Internationalization
====================

The web UI currently supports English and Simplified Chinese. Language selection
is available in Settings and is stored in browser local storage. If no saved
language preference exists, the frontend checks the browser language and uses
Simplified Chinese only for matching Chinese locales; otherwise it falls back to
English.

The bot log text itself is intentionally not translated. Logs are operational
events from the backend and remain in their original form.

Charts
======

The ``AccountStats`` plugin stores lending history in
``market_data/loan_history.sqlite3``. The first history update starts in a
background thread during plugin initialization so the first lending loop does not
wait for chart history. The ``Charts`` plugin periodically exports summarized
history to ``www/history.json``. The React charts page reads that file through
``/api/charts/history`` and renders it with ECharts.

Development Checks
==================

Useful commands for frontend work:

.. code-block:: bash

    npm test
    npm run typecheck
    npm run build

Useful commands for backend web changes:

.. code-block:: bash

    uv run pytest tests/test_WebServer.py tests/test_DashboardStatic.py -q
    uv run ruff check src/lendingbot/modules/WebServer.py tests/test_WebServer.py
    uv run mypy src/lendingbot/modules/WebServer.py

``tests/test_DashboardStatic.py`` verifies that the generated HTML points at
local Vite assets and that the legacy dashboard script has been removed.
