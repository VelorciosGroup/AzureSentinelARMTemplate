"""
Command-line interface module.

Responsibilities:
- Parse command-line arguments.
- Configure logging.
- Invoke the main processing pipeline.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .utils.logging_utils import setup_logging
from .core.transformer import run_automation


def build_parser() -> argparse.ArgumentParser:
    """
    Build and return the argument parser for the CLI.

    Returns:
        argparse.ArgumentParser: Configured parser for the `template_automation` CLI.

    Notes:
        The parser includes arguments for:
        - Master template JSON file
        - Input directory of playbooks
        - Output directory for transformed playbooks
        - Verbosity level
    """
    parser = argparse.ArgumentParser(
        prog="template_automation",
        description=(
            "Tool to apply a master template over a set of JSON playbooks."
        ),
    )

    parser.add_argument(
        "-master",
        "-m",
        dest="master_path",
        type=Path,
        required=True,
        help="Path to the master template JSON file (e.g., Deploy_CrowdStrike.json).",
    )

    parser.add_argument(
        "-dirin",
        "-i",
        dest="dir_in",
        type=Path,
        required=True,
        help="Input directory containing the playbooks to process.",
    )

    parser.add_argument(
        "-dirout",
        "-o",
        dest="dir_out",
        type=Path,
        required=True,
        help="Output directory to write the transformed playbooks.",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity level (use -v, -vv, etc.).",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """
    Main entry point for the CLI.

    Args:
        argv (list[str] | None, optional): List of command-line arguments.
            If None, `sys.argv` is used. Defaults to None.

    Returns:
        int: Exit code (0 for success).

    Notes:
        - Configures logging according to the verbosity level.
        - Executes the main automation pipeline by calling `run_automation`.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # Configure logging based on -v level
    if args.verbose >= 2:
        level = "DEBUG"
    elif args.verbose == 1:
        level = "INFO"
    else:
        level = "WARNING"

    setup_logging(level)

    # Run main automation pipeline
    run_automation(
        master_path=args.master_path,
        dir_in=args.dir_in,
        dir_out=args.dir_out,
    )

    return 0
