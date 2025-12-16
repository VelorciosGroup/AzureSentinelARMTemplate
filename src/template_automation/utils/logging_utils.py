"""
Configuración centralizada de logging.
"""

from __future__ import annotations

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """
    Configura el logging básico.

    level: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )

