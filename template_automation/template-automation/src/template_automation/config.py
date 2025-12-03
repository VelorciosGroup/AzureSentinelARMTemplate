"""
Configuración general y constantes del proyecto.
"""

from __future__ import annotations

from pathlib import Path

# Extensión de ficheros que vamos a procesar
JSON_EXTENSION = ".json"

# Nombre de subdirectorio por defecto para salida (por si lo necesitas después)
DEFAULT_OUTPUT_DIR_NAME = "out"

# Directorio base del proyecto (asumiendo layout src/)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

