"""
Funciones para escribir los resultados transformados.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from ..utils.file_system import ensure_dir_exists


def write_playbook(
    output_dir: Path,
    input_path: Path,
    playbook_data: Dict[str, Any],
) -> Path:
    """
    Escribe el playbook transformado en output_dir, usando el mismo nombre de fichero.

    Devuelve la ruta final al archivo escrito.
    """
    ensure_dir_exists(output_dir)

    output_path = output_dir / input_path.name

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(playbook_data, f, indent=2, ensure_ascii=False)

    return output_path
