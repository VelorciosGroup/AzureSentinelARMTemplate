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
   - Transforma:
       * workflows_*_externalid
       * connections_azure*_externalid
       * connections_keyvault*_externalid
     Para cada uno:
       * Crea una variable var_<nombre_param>:
         - workflows_*_externalid  → concat con Microsoft.Logic/workflows
         - connections_azure*_externalid → concat('<connector>-', parameters('<workflow_name_param>'))
         - connections_keyvault*_externalid → [variables('keyvault_Connection_Name')]
           y además crea/ajusta:
             keyvault_Connection_Name = "[concat('keyvault-', parameters('keyvault_Name'))]"
       * Sustituye todas las ocurrencias de "[parameters('<nombre_param>')]" por
         "[variables('var_<nombre_param>')]".
     Además:
       * Para connections_azure*_externalid:
           - Inserta en el workflow el bloque $connections del conector
           - Añade dependsOn y recurso Microsoft.Web/connections (<connector>)
       * Para connections_keyvault*_externalid:
           - Inserta en el workflow el bloque $connections de keyvault
           - Añade dependsOn y recurso Microsoft.Web/connections (estructura especial)
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

# Patrones regex
RE_WORKFLOW_NAME = re.compile(r"workflows_.*_name")
RE_WORKFLOW_EXTERNALID = re.compile(r"workflows_.*_externalid")
RE_CONNECTION_AZURE_EXTERNALID = re.compile(r"connections_azure.*_externalid")
RE_CONNECTION_KEYVAULT_EXTERNALID = re.compile(r"connections_keyvault.*_externalid")


def get_deployment_names_from_master(master_template: Dict[str, Any]) -> List[str]:
    resources = master_template.get("resources", [])
    if not isinstance(resources, list):
        logger.warning("La master template no tiene un array 'resources' válido.")
        return []

    deployment_names: List[str] = []

    for res in resources:
        if not isinstance(res, dict):
            continue

        if res.get("type") != "Microsoft.Resources/deployments":
            continue

        name = res.get("name")
        if isinstance(name, str):
            deployment_names.append(name)
        else:
            logger.debug("Recurso sin nombre string: %r", res)

    return deployment_names


def inspect_workflow_parameters(playbook: Dict[str, Any], source_name: str) -> None:
    params = playbook.get("parameters", {})

    if not isinstance(params, dict):
        logger.warning("El playbook %s no tiene un objeto 'parameters' válido.", source_name)
        return

    print("=" * 80)
    print(f"Parámetros workflows_ en: {source_name}")
    print("=" * 80)

    found_any = False

    for key, definition in params.items():
        if not isinstance(key, str) or not isinstance(definition, dict):
            continue

        if RE_WORKFLOW_NAME.fullmatch(key):
            param_kind = "WORKFLOW_NAME"
        elif RE_WORKFLOW_EXTERNALID.fullmatch(key):
            param_kind = "WORKFLOW_EXTERNALID"
        else:
            continue

        default_value = definition.get("defaultValue")
        found_any = True
        print(f"[{param_kind}] {key} -> defaultValue={default_value!r}")

    if not found_any:
        print("No se han encontrado parámetros workflows_ con sufijo _name o _externalid.")
    print()


# ---------------------------------------------------------------------------
# workflows_*_externalid → variables
# ---------------------------------------------------------------------------
def _add_workflow_externalid_variables(playbook: Dict[str, Any]) -> List[str]:
    params = playbook.get("parameters", {})
    if not isinstance(params, dict):
        return []

    externalid_params: List[str] = []

    for key, definition in params.items():
        if not isinstance(key, str) or not isinstance(definition, dict):
            continue
        if not RE_WORKFLOW_EXTERNALID.fullmatch(key):
            continue
        externalid_params.append(key)

    if not externalid_params:
        return []

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
        logger.debug("Creada variable %s = %s", var_name, expression)

    return externalid_params


# ---------------------------------------------------------------------------
# connections_azure*_externalid → variables
# ---------------------------------------------------------------------------
def _add_connection_azure_externalid_variables(playbook: Dict[str, Any]) -> List[str]:
    params = playbook.get("parameters", {})
    if not isinstance(params, dict):
        return []

    externalid_params: List[str] = []

    for key, definition in params.items():
        if not isinstance(key, str) or not isinstance(definition, dict):
            continue
        if not RE_CONNECTION_AZURE_EXTERNALID.fullmatch(key):
            continue
        externalid_params.append(key)

    if not externalid_params:
        return []

    variables = playbook.get("variables")
    if not isinstance(variables, dict):
        variables = {}
        playbook["variables"] = variables

    for param_name in externalid_params:
        var_name = f"var_{param_name}"

        # connections_<connector>_<resto>_externalid
        parts = param_name.split("_")
        connector = parts[1] if len(parts) > 1 else "azuresentinel"
        middle_parts = parts[2:-1] if len(parts) > 3 else []
        middle = "_".join(middle_parts) if middle_parts else ""

        if middle:
            workflow_param_name = f"workflows_{middle}_name"
        else:
            workflow_param_name = "PlaybookName"

        if workflow_param_name not in params:
            logger.warning(
                "No se encontró el parámetro de nombre de workflow esperado '%s'. "
                "Se usará 'PlaybookName' como fallback.",
                workflow_param_name,
            )
            workflow_param_name = "PlaybookName"

        expression = (
            "[concat('"
            + connector
            + "-', parameters('"
            + workflow_param_name
            + "'))]"
        )

        if var_name in variables:
            logger.info(
                "La variable %s ya existe, no se sobrescribe (valor actual: %r).",
                var_name,
                variables[var_name],
            )
            continue

        variables[var_name] = expression
        logger.debug("Creada variable %s = %s", var_name, expression)

    return externalid_params


# ---------------------------------------------------------------------------
# connections_keyvault*_externalid → variables
# ---------------------------------------------------------------------------
def _add_connection_keyvault_externalid_variables(playbook: Dict[str, Any]) -> List[str]:
    """
    Para cada parámetro connections_keyvault.*_externalid:
      - Crea (si no existe) la variable:
          keyvault_Connection_Name =
            "[concat('keyvault-', parameters('keyvault_Name'))]"
      - Crea una variable:
          var_<param_name> = "[variables('keyvault_Connection_Name')]"
    """
    params = playbook.get("parameters", {})
    if not isinstance(params, dict):
        return []

    externalid_params: List[str] = []

    for key, definition in params.items():
        if not isinstance(key, str) or not isinstance(definition, dict):
            continue
        if not RE_CONNECTION_KEYVAULT_EXTERNALID.fullmatch(key):
            continue
        externalid_params.append(key)

    if not externalid_params:
        return []

    variables = playbook.get("variables")
    if not isinstance(variables, dict):
        variables = {}
        playbook["variables"] = variables

    # Aseguramos keyvault_Connection_Name
    if "keyvault_Connection_Name" not in variables:
        if "keyvault_Name" in params:
            variables["keyvault_Connection_Name"] = (
                "[concat('keyvault-', parameters('keyvault_Name'))]"
            )
        else:
            logger.warning(
                "No se encontró parámetro 'keyvault_Name'. "
                "Se creará keyvault_Connection_Name con un valor fijo."
            )
            variables["keyvault_Connection_Name"] = "'keyvault-connection'"

    for param_name in externalid_params:
        var_name = f"var_{param_name}"
        expression = "[variables('keyvault_Connection_Name')]"

        if var_name in variables:
            logger.info(
                "La variable %s ya existe, no se sobrescribe (valor actual: %r).",
                var_name,
                variables[var_name],
            )
            continue

        variables[var_name] = expression
        logger.debug("Creada variable %s = %s", var_name, expression)

    return externalid_params


# ---------------------------------------------------------------------------
# Reemplazar [parameters()] → [variables()]
# ---------------------------------------------------------------------------
def _replace_parameters_with_variables(
    playbook: Dict[str, Any],
    param_names: List[str],
) -> None:
    if not param_names:
        return

    replacements = {
        f"[parameters('{param_name}')]": f"[variables('var_{param_name}')]"
        for param_name in param_names
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


# ---------------------------------------------------------------------------
# Bloques de conexiones Azure (azuresentinel, azuremonitorlogs, ...)
# ---------------------------------------------------------------------------
def _ensure_azure_connections_blocks(
    playbook: Dict[str, Any],
    connection_param_names: List[str],
) -> None:
    if not connection_param_names:
        return

    resources = playbook.get("resources", [])
    if not isinstance(resources, list):
        return

    conn_info = {}
    for param_name in connection_param_names:
        parts = param_name.split("_")
        connector = parts[1] if len(parts) > 1 else "azuresentinel"
        var_name = f"var_{param_name}"
        depends_expr = f"[resourceId('Microsoft.Web/connections', variables('{var_name}'))]"
        api_id_expr = (
            "[concat('/subscriptions/', subscription().subscriptionId, "
            f"'/providers/Microsoft.Web/locations/', resourceGroup().location, '/managedApis/{connector}')]"
        )

        conn_info[param_name] = {
            "connector": connector,
            "var_name": var_name,
            "depends_expr": depends_expr,
            "api_id_expr": api_id_expr,
        }

    # Ajustar workflows
    for res in resources:
        if not isinstance(res, dict):
            continue
        if res.get("type") != "Microsoft.Logic/workflows":
            continue

        props = res.get("properties")
        if not isinstance(props, dict):
            props = {}
            res["properties"] = props

        parameters = props.get("parameters")
        if not isinstance(parameters, dict):
            parameters = {}
            props["parameters"] = parameters

        connections = parameters.get("$connections")
        if not isinstance(connections, dict):
            connections = {}
            parameters["$connections"] = connections

        value = connections.get("value")
        if not isinstance(value, dict):
            value = {}
            connections["value"] = value

        depends_on = res.get("dependsOn")
        if not isinstance(depends_on, list):
            depends_on = []
            res["dependsOn"] = depends_on

        for _, info in conn_info.items():
            connector = info["connector"]
            var_name = info["var_name"]
            depends_expr = info["depends_expr"]
            api_id_expr = info["api_id_expr"]

            value[connector] = {
                "connectionId": (
                    f"[resourceId('Microsoft.Web/connections', variables('{var_name}'))]"
                ),
                "connectionName": f"[variables('{var_name}')]",
                "id": api_id_expr,
                "connectionProperties": {
                    "authentication": {
                        "type": "ManagedServiceIdentity",
                    }
                },
            }

            if depends_expr not in depends_on:
                depends_on.append(depends_expr)

    # Recursos Microsoft.Web/connections
    for _, info in conn_info.items():
        connector = info["connector"]
        var_name = info["var_name"]
        api_id_expr = info["api_id_expr"]

        exists = False
        for res in resources:
            if (
                isinstance(res, dict)
                and res.get("type") == "Microsoft.Web/connections"
                and res.get("name") == f"[variables('{var_name}')]"
            ):
                exists = True
                break

        if exists:
            continue

        conn_resource = {
            "type": "Microsoft.Web/connections",
            "apiVersion": "2016-06-01",
            "name": f"[variables('{var_name}')]",
            "location": "[resourceGroup().location]",
            "kind": "V1",
            "properties": {
                "displayName": f"[variables('{var_name}')]",
                "customParameterValues": {},
                "parameterValueType": "Alternative",
                "api": {
                    "id": api_id_expr,
                },
            },
        }

        resources.append(conn_resource)


# ---------------------------------------------------------------------------
# Bloques de conexión Key Vault (estructura especial)
# ---------------------------------------------------------------------------
def _ensure_keyvault_connections_blocks(
    playbook: Dict[str, Any],
    connection_param_names: List[str],
) -> None:
    if not connection_param_names:
        return

    resources = playbook.get("resources", [])
    if not isinstance(resources, list):
        return

    # Datos fijos para keyvault
    var_conn_name = "keyvault_Connection_Name"
    conn_name_expr = f"[variables('{var_conn_name}')]"
    api_id_expr = (
        "[concat(subscription().id, '/providers/Microsoft.Web/locations/', "
        "resourceGroup().location, '/managedApis/', 'keyvault')]"
    )
    depends_expr = (
        "[resourceId('Microsoft.Web/connections', variables('keyvault_Connection_Name'))]"
    )

    # 1) Ajustar workflows
    for res in resources:
        if not isinstance(res, dict):
            continue
        if res.get("type") != "Microsoft.Logic/workflows":
            continue

        props = res.get("properties")
        if not isinstance(props, dict):
            props = {}
            res["properties"] = props

        parameters = props.get("parameters")
        if not isinstance(parameters, dict):
            parameters = {}
            props["parameters"] = parameters

        connections = parameters.get("$connections")
        if not isinstance(connections, dict):
            connections = {}
            parameters["$connections"] = connections

        value = connections.get("value")
        if not isinstance(value, dict):
            value = {}
            connections["value"] = value

        depends_on = res.get("dependsOn")
        if not isinstance(depends_on, list):
            depends_on = []
            res["dependsOn"] = depends_on

        # Bloque keyvault en $connections
        value["keyvault"] = {
            "connectionId": (
                "[resourceId('Microsoft.Web/connections', variables('keyvault_Connection_Name'))]"
            ),
            "connectionName": conn_name_expr,
            "id": api_id_expr,
            "connectionProperties": {
                "authentication": {
                    "type": "ManagedServiceIdentity",
                }
            },
        }

        if depends_expr not in depends_on:
            depends_on.append(depends_expr)

    # 2) Recurso Microsoft.Web/connections para keyvault
    exists = False
    for res in resources:
        if (
            isinstance(res, dict)
            and res.get("type") == "Microsoft.Web/connections"
            and res.get("name") == conn_name_expr
        ):
            exists = True
            break

    if not exists:
        conn_resource = {
            "type": "Microsoft.Web/connections",
            "apiVersion": "2016-06-01",
            "name": conn_name_expr,
            "location": "[resourceGroup().location]",
            "properties": {
                "api": {
                    "id": api_id_expr,
                },
                "displayName": conn_name_expr,
                "parameterValueType": "Alternative",
                "AlternativeParameterValues": {
                    "vaultName": "[parameters('keyvault_Name')]",
                },
            },
        }
        resources.append(conn_resource)


# ---------------------------------------------------------------------------
# Transformación principal
# ---------------------------------------------------------------------------
def transform_playbook(
    playbook: Dict[str, Any],
    master_template: Dict[str, Any],  # noqa: ARG001
) -> Dict[str, Any]:
    logger.debug("Iniciando transformación de playbook (externalid).")

    wf_params = _add_workflow_externalid_variables(playbook)
    conn_azure_params = _add_connection_azure_externalid_variables(playbook)
    conn_kv_params = _add_connection_keyvault_externalid_variables(playbook)

    all_params = wf_params + conn_azure_params + conn_kv_params

    if all_params:
        logger.info("Variables creadas para parámetros *_externalid: %s", all_params)
        _replace_parameters_with_variables(playbook, all_params)
    else:
        logger.debug("No se encontraron parámetros *_externalid relevantes en este playbook.")

    _ensure_azure_connections_blocks(playbook, conn_azure_params)
    _ensure_keyvault_connections_blocks(playbook, conn_kv_params)

    logger.debug("Transformación de *_externalid completada.")
    return playbook


def run_automation(
    master_path: Path,
    dir_in: Path,
    dir_out: Path,
) -> None:
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

        inspect_workflow_parameters(playbook_data, source_name=file_name)

        transformed = transform_playbook(playbook_data, master_template)

        logger.info("Guardando playbook en el directorio de salida...")
        saved_path = write_playbook(dir_out, playbook_path, transformed)
        logger.info("Playbook guardado correctamente en: %s", saved_path)
