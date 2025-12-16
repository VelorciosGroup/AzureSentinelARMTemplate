"""
Centralized logging configuration.
"""

from __future__ import annotations

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """
    Configure basic logging for the application.

    Args:
        level (str, optional): Logging level. One of "DEBUG", "INFO",
            "WARNING", "ERROR", "CRITICAL". Defaults to "INFO".

    Notes:
        Uses `logging.basicConfig` to configure the root logger with:
        - Specified logging level.
        - Format: "%(asctime)s [%(levelname)s] %(name)s: %(message)s".
        - Output stream: `sys.stdout`.
        If an invalid level is provided, defaults to INFO.
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )
