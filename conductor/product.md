# Initial Concept
The user wants to migrate the existing Mika Lending Bot to Python 3 for maintenance and long-term viability.

# Product Guide - Mika Lending Bot

## Initial Concept
Mika Lending Bot is an automated cryptocurrency lending tool designed for exchanges like Poloniex and Bitfinex. The current focus is migrating the project to Python 3.12+ to ensure long-term maintainability, security, and performance.

## Target Users
- **Passive Cryptocurrency Investors:** Individuals looking to earn passive yield on their crypto assets through automated lending.
- **Developers:** Users seeking a robust, extensible framework for building or customizing lending bot strategies.

## Strategic Goals
- **Lending Strategy Optimization:** Improve and refine strategies to maximize interest yield in volatile markets.
- **System Stability & Security:** Enhance the robustness of the automated operation for safe, long-term use.
- **Developer Experience:** Refactor the codebase to streamline the addition of new exchanges and modular components.
- **Robust Test Coverage:** Maintain a high standard of testing with a target of >80% coverage for core logic and >60% for auxiliary modules to ensure code quality and prevent regressions.
- **Python 3 Modernization:** Complete the transition to Python 3.12+ to leverage modern language features and maintainability.

## Key Features & Technical Requirements
- **Modern Migration:** Full migration of syntax and libraries to Python 3.12+, removing legacy Python 2 dependencies.
- **Modern Tooling:** Integration of `uv` for dependency management, `ruff` for linting/formatting, and `mypy` for strict type checking.
- **Containerization:** Update Docker and Docker Compose configurations for seamless, cross-environment deployment.
- **Modular Exchange API:** Refactor exchange integrations into a more pluggable architecture.
