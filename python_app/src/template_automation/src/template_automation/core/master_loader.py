"""
Funciones para cargar y validar la master template.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from ..utils.validation import validate_master_template


def load_master_template(path: Path) -> Dict[str, Any]:
    """
    Carga un fichero JSON de master template y devuelve el dict.

    Lanza FileNotFoundError / json.JSONDecodeError si algo va mal.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Master template no encontrada: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # Validación (de momento solo stub, pero así ya dejas el hook)
    validate_master_template(data)

    return data
