"""
General project configuration and constants.

Constants:
- JSON_EXTENSION (str): File extension to process (default: ".json").
- DEFAULT_OUTPUT_DIR_NAME (str): Default subdirectory name for output (default: "out").
- PROJECT_ROOT (Path): Project root directory, assuming a `src/` layout.
"""
from __future__ import annotations

from pathlib import Path

JSON_EXTENSION: str = ".json"
DEFAULT_OUTPUT_DIR_NAME: str = "out"
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
