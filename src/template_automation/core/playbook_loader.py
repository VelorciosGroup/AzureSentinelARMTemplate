"""
Funciones para descubrir y cargar playbooks desde un directorio.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from ..config import JSON_EXTENSION
from ..utils.file_system import iter_json_files


def discover_playbooks(dir_in: Path) -> List[Path]:
    """
    Devuelve la lista de rutas de playbooks JSON dentro de `dir_in`.
    """
    if not dir_in.is_dir():
        raise NotADirectoryError(f"Directorio de entrada no válido: {dir_in}")

    return list(iter_json_files(dir_in, extension=JSON_EXTENSION))


def load_playbook(path: Path) -> Dict[str, Any]:
    """
    Carga un playbook JSON y devuelve el dict.
    """
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data
