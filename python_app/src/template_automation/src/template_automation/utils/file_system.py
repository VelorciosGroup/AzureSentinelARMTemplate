"""
Utilidades relacionadas con el sistema de ficheros.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable


def ensure_dir_exists(path: Path) -> None:
    """
    Crea el directorio (y padres) si no existe.
    """
    path.mkdir(parents=True, exist_ok=True)


def iter_json_files(directory: Path, extension: str = ".json") -> Iterable[Path]:
    """
    Itera recursivamente sobre todos los ficheros con la extensión dada
    dentro de `directory`.
    """
    if not directory.is_dir():
        return []

    yield from directory.rglob(f"*{extension}")
