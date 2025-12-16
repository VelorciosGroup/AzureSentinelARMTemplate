"""
Functions to load and validate the master template.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from ..utils.validation import validate_master_template


def load_master_template(path: Path) -> Dict[str, Any]:
    """
    Load a JSON master template file and return it as a dictionary.

    Args:
        path (Path): Path to the master template JSON file.

    Returns:
        Dict[str, Any]: Parsed JSON data as a dictionary.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file content is not valid JSON.

    Notes:
        This function also calls `validate_master_template` to perform 
        validation on the loaded data. Currently, this is a stub for future validation logic.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Master template no encontrada: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # Validación (de momento solo stub, pero así ya dejas el hook)
    validate_master_template(data)

    return data
