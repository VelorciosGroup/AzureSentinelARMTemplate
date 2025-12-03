"""
Lógica de transformación principal.

Flujo actual:

1. Carga la master template.
2. Extrae los nombres de los deployments (playbooks) de la master.
3. Para cada nombre N busca en dir_in el fichero `Cliente_N.json`.
4. Si existe:
   - Lo carga.
   - Identifica y muestra por pantalla los parámetros:
       * workflows_*_name
       * workflows_*_externalid
   - Para cada workflows_*_externalid:
       * Crea una variable var_<nombre_param> con valor:
         "[concat('/subscriptions/', subscription().subscriptionId, '/resourceGroups/', resourceGroup().name ,'/providers/Microsoft.Logic/workflows/', parameters('<nombre_param>'))]"
       * Sustituye todas las ocurrencias de "[parameters('<nombre_param>')]" por
         "[variables('var_<nombre_param>')]"
   - Lo guarda en dir_out.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List

from .master_loader import load_master_template
from .playbook_loader import load_playbook
from .writer import write_playbook

logger = logging.getLogger(__name__)

# Patrones regex para parámetros workflows
RE_WORKFLOW_NAME = re.compile(r"workflows_.*_name")
RE_WORKFLOW_EXTERNALID = re.compile(r"workflows_.*_externalid")


def get_deployment_names_from_master(master_template: Dict[str, Any]) -> List[str]:
    """
    Extrae de la master template los nombres de los recursos de tipo
    'Microsoft.Resources/deployments'.
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


def inspect_workflow_parameters(playbook: Dict[str, Any], source_name: str) -> None:
    """
    Inspecciona los parámetros del ARM template de un playbook y muestra por pantalla
    los parámetros que:
      - cumplen workflows_.*_name
      - o workflows_.*_externalid

    Solo los muestra, no modifica nada.
    """
    params = playbook.get("parameters", {})

    if not isinstance(params, dict):
        logger.warning("El playbook %s no tiene un objeto 'parameters' válido.", source_name)
        return

    print("=" * 80)
    print(f"Parámetros workflows_ en: {source_name}")
    print("=" * 80)

    found_any = False

    for key, definition in params.items():
        if not isinstance(key, str):
            continue
        if not isinstance(definition, dict):
            continue

        if RE_WORKFLOW_NAME.fullmatch(key):
            param_kind = "WORKFLOW_NAME"
        elif RE_WORKFLOW_EXTERNALID.fullmatch(key):
            param_kind = "WORKFLOW_EXTERNALID"
        else:
            # No coincide con ningún patrón workflows_.*_name / workflows_.*_externalid
            continue

        default_value = definition.get("defaultValue")
        found_any = True
        print(f"[{param_kind}] {key} -> defaultValue={default_value!r}")

    if not found_any:
        print("No se han encontrado parámetros workflows_ con sufijo _name o _externalid.")
    print()  # línea en blanco final


def _add_externalid_variables(playbook: Dict[str, Any]) -> List[str]:
    """
    Para cada parámetro que cumpla workflows_.*_externalid crea una variable:

      var_<nombre_param> =
        "[concat('/subscriptions/', subscription().subscriptionId,
                 '/resourceGroups/', resourceGroup().name ,
                 '/providers/Microsoft.Logic/workflows/',
                 parameters('<nombre_param>'))]"

    Devuelve la lista de nombres de parámetro workflows_*_externalid encontrados.
    """
    params = playbook.get("parameters", {})
    if not isinstance(params, dict):
        return []

    externalid_params: List[str] = []

    for key, definition in params.items():
        if not isinstance(key, str):
            continue
        if not isinstance(definition, dict):
            continue

        if not RE_WORKFLOW_EXTERNALID.fullmatch(key):
            continue

        externalid_params.append(key)

    if not externalid_params:
        return []

    # Aseguramos que exista el objeto variables
    variables = playbook.get("variables")
    if not isinstance(variables, dict):
        variables = {}
        playbook["variables"] = variables

    for param_name in externalid_params:
        var_name = f"var_{param_name}"
        expression = (
            "[concat('/subscriptions/', subscription().subscriptionId, "
            "'/resourceGroups/', resourceGroup().name ,"
            "'/providers/Microsoft.Logic/workflows/', "
            f"parameters('{param_name}'))]"
        )

        if var_name in variables:
            logger.info(
                "La variable %s ya existe, no se sobrescribe (valor actual: %r).",
                var_name,
                variables[var_name],
            )
            continue

        variables[var_name] = expression
        logger.debug(
            "Creada variable %s = %s",
            var_name,
            expression,
        )

    return externalid_params


def _replace_parameters_with_variables(
    playbook: Dict[str, Any],
    externalid_params: List[str],
) -> None:
    """
    Recorre todo el playbook y reemplaza:

      "[parameters('<nombre_param>')]"

    por:

      "[variables('var_<nombre_param>')]"

    para cada nombre de parámetro en externalid_params.
    """
    if not externalid_params:
        return

    replacements = {
        f"[parameters('{param_name}')]": f"[variables('var_{param_name}')]"
        for param_name in externalid_params
    }

    def _walk(obj: Any) -> Any:
        if isinstance(obj, dict):
            for k, v in obj.items():
                obj[k] = _walk(v)
            return obj

        if isinstance(obj, list):
            for i, v in enumerate(obj):
                obj[i] = _walk(v)
            return obj

        if isinstance(obj, str):
            s = obj
            for old, new in replacements.items():
                if old in s:
                    s = s.replace(old, new)
            return s

        return obj

    _walk(playbook)


def transform_playbook(
    playbook: Dict[str, Any],
    master_template: Dict[str, Any],  # noqa: ARG001 (no lo usamos todavía)
) -> Dict[str, Any]:
    """
    Aplica la lógica de transformación sobre el playbook:

    - Detecta parámetros workflows_.*_externalid.
    - Crea variables var_<nombre_param> con el concat de subscription/resourceGroup/workflow.
    - Reemplaza todas las ocurrencias de "[parameters('<nombre_param>')]" por
      "[variables('var_<nombre_param>')]".
    """
    logger.debug("Iniciando transformación de playbook (workflow_*_externalid).")

    externalid_params = _add_externalid_variables(playbook)
    if not externalid_params:
        logger.debug("No se encontraron parámetros workflows_*_externalid en este playbook.")
        return playbook

    logger.info(
        "Se han creado variables para los siguientes parámetros workflows_*_externalid: %s",
        externalid_params,
    )

    _replace_parameters_with_variables(playbook, externalid_params)

    logger.debug("Transformación de workflows_*_externalid completada.")
    return playbook


def run_automation(
    master_path: Path,
    dir_in: Path,
    dir_out: Path,
) -> None:
    """
    1. Carga master template.
    2. Extrae nombres de deployments.
    3. Por cada nombre busca Cliente_<name>.json en dir_in.
    4. Si existe:
        - lo carga
        - muestra por pantalla los parámetros workflows_*_name y workflows_*_externalid
        - aplica la transformación de workflows_*_externalid
        - lo guarda en dir_out
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

        # Mostrar por pantalla los parámetros de interés
        inspect_workflow_parameters(playbook_data, source_name=file_name)

        # Aplicar transformación sobre workflows_*_externalid
        transformed = transform_playbook(playbook_data, master_template)

        # Guardar en el directorio de salida
        logger.info("Guardando playbook en el directorio de salida...")
        saved_path = write_playbook(dir_out, playbook_path, transformed)
        logger.info("Playbook guardado correctamente en: %s", saved_path)
