"""
Lógica de transformación principal.

De momento:
- Lee la master template.
- Extrae los nombres de los despliegues (playbooks) de la sección `resources`.
- Para cada nombre N, busca en dir_in el fichero `Cliente_N.json`.
- Si existe, lo carga y lo muestra por pantalla.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from .master_loader import load_master_template
from .playbook_loader import load_playbook

logger = logging.getLogger(__name__)


def get_deployment_names_from_master(master_template: Dict[str, Any]) -> List[str]:
    """
    Extrae de la master template los nombres de los recursos de tipo
    'Microsoft.Resources/deployments'.

    En tu ejemplo devolvería algo como:
    [
        "OrchestatorPart_CrowdStrike_Auth_Playbook",
        "OrchestatorPart_CrowdStrike_Block_IOC_Playbook",
        "Action_CrowdStrike_Device_Isolation_Playbook",
        ...
    ]
    """
    resources = master_template.get("resources", [])
    if not isinstance(resources, list):
        logger.warning("La master template no tiene un array 'resources' válido.")
        return []

    deployment_names: List[str] = []

    for res in resources:
        if not isinstance(res, dict):
            continue

        if res.get("type") != "Microsoft.Resources/deployments":
            # Solo nos interesan los deployments (cada uno corresponde a un playbook)
            continue

        name = res.get("name")
        if isinstance(name, str):
            deployment_names.append(name)
        else:
            logger.debug("Recurso sin nombre string: %r", res)

    return deployment_names


def transform_playbook(
    playbook: Dict[str, Any],
    master_template: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Placeholder para futura lógica de transformación.

    Ahora mismo no se usa, pero lo dejamos preparado para cuando quieras
    empezar a modificar la estructura de los playbooks "malos".
    """
    logger.debug("Transformación no implementada aún. Devolviendo playbook sin cambios.")
    return playbook


def run_automation(
    master_path: Path,
    dir_in: Path,
    dir_out: Path,  # ahora mismo no se usa, pero lo dejamos para el futuro
) -> None:
    """
    Flujo actual:

    1. Carga la master template.
    2. Extrae los nombres de los deployments (playbooks) de la master.
    3. Para cada nombre N busca en `dir_in` el fichero `Cliente_N.json`.
    4. Si lo encuentra:
        - Lo carga.
        - Muestra su contenido por pantalla (JSON pretty).
    """

    logger.info("Cargando master template desde %s", master_path)
    master_template = load_master_template(master_path)

    logger.info("Extrayendo nombres de deployments desde la master template")
    deployment_names = get_deployment_names_from_master(master_template)

    if not deployment_names:
        logger.warning("No se han encontrado deployments en la master template.")
        return

    logger.info("Se han encontrado %d deployments: %s", len(deployment_names), deployment_names)

    for name in deployment_names:
        file_name = f"Cliente_{name}.json"
        playbook_path = dir_in / file_name

        if not playbook_path.is_file():
            logger.warning("No se encontró el playbook esperado: %s", playbook_path)
            continue

        logger.info("Leyendo playbook: %s", playbook_path)
        playbook_data = load_playbook(playbook_path)

        # Mostrar por pantalla el contenido del archivo
        print("=" * 80)
        print(f"Playbook: {file_name}")
        print("=" * 80)
        print(json.dumps(playbook_data, indent=2, ensure_ascii=False))
        print()  # línea en blanco al final para separar
