"""
LendingBot main entry point

This is the main entry point for the application, responsible for:
- Parsing command line arguments
- Instantiating and running the BotOrchestrator
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import NoReturn

from .modules.Orchestrator import BotOrchestrator


def parse_arguments() -> argparse.Namespace:
    """
    Parses command line arguments

    Returns:
        argparse.Namespace: Parsed arguments object
    """
    parser = argparse.ArgumentParser(
        description="LendingBot - Cryptocurrency Lending Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-cfg",
        "--config",
        help="Custom configuration file path (default: default.toml)",
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
    """
    # Allow running from different directories
    if not Path("pyproject.toml").exists():
        os.chdir(Path(sys.argv[0]).resolve().parent)

    # Parse command line arguments
    args = parse_arguments()

    # Determine config path
    config_path = Path(args.config) if args.config else Path("config.toml")

    # Create and run orchestrator
    bot = BotOrchestrator(config_path, dry_run=bool(args.dryrun))
    bot.initialize()
    bot.run()


if __name__ == "__main__":
    main()
