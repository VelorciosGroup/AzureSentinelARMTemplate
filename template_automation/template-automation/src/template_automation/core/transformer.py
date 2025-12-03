"""
Lógica de transformación principal.

Aquí es donde luego vas a meter la magia:
- Combinar master template con cada playbook
- Parametrizar, reemplazar, etc.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

from .master_loader import load_master_template
from .playbook_loader import discover_playbooks, load_playbook
from .writer import write_playbook

logger = logging.getLogger(__name__)


def transform_playbook(
    playbook: Dict[str, Any],
    master_template: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Aplica la lógica de transformación a un playbook concreto.

    De momento: devuelve el playbook tal cual (no destructivo).
    Aquí luego puedes:
      - Mezclar secciones de la master
      - Aplicar parámetros
      - Normalizar conexiones, etc.
    """
    # TODO: implementar lógica real de transformación.
    # Por ahora, solo logueamos y devolvemos el original.
    logger.debug("Transformando playbook (placeholder sin cambios).")
    return playbook


def run_automation(
    master_path: Path,
    dir_in: Path,
    dir_out: Path,
) -> None:
    """
    Orquesta el flujo completo:
    - Cargar master template
    - Descubrir playbooks en dir_in
    - Transformar cada uno
    - Escribir resultados en dir_out
    """
    logger.info("Cargando master template desde %s", master_path)
    master_template = load_master_template(master_path)

    logger.info("Buscando playbooks en %s", dir_in)
    playbook_paths: List[Path] = discover_playbooks(dir_in)
    logger.info("Se han encontrado %d playbooks", len(playbook_paths))

    if not playbook_paths:
        logger.warning("No se encontraron playbooks para procesar.")
        return

    for pb_path in playbook_paths:
        logger.info("Procesando playbook: %s", pb_path)
        playbook_data = load_playbook(pb_path)
        transformed = transform_playbook(playbook_data, master_template)
        output_path = write_playbook(dir_out, pb_path, transformed)
        logger.info("Playbook escrito en: %s", output_path)

    logger.info("Procesamiento completado.")
