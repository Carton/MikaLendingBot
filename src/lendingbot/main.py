"""
LendingBot main entry point

This is the main entry point for the application, responsible for:
- Parsing command line arguments
- Loading configuration
- Initializing various modules
- Starting the main loop and Web server
"""

from __future__ import annotations

import argparse
import sys
from typing import NoReturn

from .modules import Configuration as Config
from .modules.Logger import Logger


# Add type hints and docstrings
def parse_arguments() -> argparse.Namespace:
    """
    Parses command line arguments

    Returns:
        argparse.Namespace: Parsed arguments object

    Command line arguments:
        -cfg, --config: Custom configuration file path
        -dry, --dryrun: Dry-run mode, does not execute actual trades
    """
    parser = argparse.ArgumentParser(
        description="LendingBot - Cryptocurrency Lending Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-cfg",
        "--config",
        help="Custom configuration file path (default: default.cfg)",
        type=str,
        default=None,
    )

    parser.add_argument(
        "-dry",
        "--dryrun",
        help="Dry-run mode, does not execute actual trades",
        action="store_true",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        help="Verbose output mode",
        action="store_true",
    )

    return parser.parse_args()


def main() -> NoReturn:
    """
    LendingBot main entrance function

    This is the main entry point for the application. Executes the following steps:
    1. Parses command line arguments
    2. Loads configuration file
    3. Initializes logging system
    4. Connects to exchange APIs
    5. Starts lending engine
    6. Starts Web server (if enabled in config)
    7. Enters main loop

    Example:
        >>> # Run with default config
        >>> python -m lendingbot.main

        >>> # Run with custom config
        >>> python -m lendingbot.main --config=myconfig.cfg

        >>> # Dry-run mode
        >>> python -m lendingbot.main --dryrun

    Raises:
        SystemExit: When the program exits
    """
    # Parse command line arguments
    args = parse_arguments()

    # 1. Load config
    config_file = args.config or "default.cfg"
    Config.init(config_file)

    # 2. Setup logging
    log = Logger()
    log.log("LendingBot v0.1.0 - Python 3 version started")
    log.log(f"Config file: {config_file}")
    log.log(f"Dry run: {args.dryrun}")

    print("⚠️  Note: This is a modernized Python 3 scaffold, code migration is in progress...")
    print("\n📚 Migration Guide:")
    print("   1. Migrate modules from modules/ directory to src/lendingbot/")
    print("   2. Migrate plugins from plugins/ directory to src/lendingbot/plugins/")
    print("   3. Update Python 2.7 syntax to Python 3.12+")
    print("   4. Add type hints and docstrings")
    print("   5. Update import statements (e.g., httplib → http.client)")

    sys.exit(0)


if __name__ == "__main__":
    main()
