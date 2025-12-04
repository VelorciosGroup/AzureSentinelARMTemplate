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
       * connections_keyvault*_externalid
     Para cada uno:
       * Crea una variable var_<nombre_param>:
         - workflows_*_externalid  → concat con Microsoft.Logic/workflows
         - connections_keyvault*_externalid → [variables('keyvault_Connection_Name')]
           y además crea/ajusta:
             keyvault_Connection_Name = "[concat('keyvault-', parameters('keyvault_Name'))]"
       * Sustituye todas las ocurrencias de "[parameters('<nombre_param>')]" por
         "[variables('var_<nombre_param>')]".
   - Además, para **cada playbook**:
       * Crea/actualiza la variable:
           AzureSentinelConnectionName =
             "[concat('azuresentinel-', parameters('<nombredelplaybook>'))]"
     Y luego:
       * Inserta/ajusta en cada workflow el bloque $connections con:
           - azuresentinel (AzureSentinelConnectionName)
           - keyvault (keyvault_Connection_Name, si existe)
       * Añade dependsOn a ambas conexiones.
       * Añade los recursos Microsoft.Web/connections para
           - AzureSentinelConnectionName (azuresentinel)
           - keyvault_Connection_Name (keyvault), con estructura especial.
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
    """
    Muestra por pantalla workflows_*_name y workflows_*_externalid.
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
# AzureSentinelConnectionName por playbook
# ---------------------------------------------------------------------------
def _ensure_azuresentinel_connection_name(playbook: Dict[str, Any]) -> None:
    """
    Para cada playbook asegura que exista la variable:

      AzureSentinelConnectionName =
        "[concat('azuresentinel-', parameters('<nombredelplaybook>'))]"

    donde <nombredelplaybook> se toma del primer parámetro workflows_.*_name
    encontrado. Si no hay ninguno, se usa 'PlaybookName' como fallback.
    """
    params = playbook.get("parameters", {})
    if not isinstance(params, dict):
        logger.warning(
            "Playbook sin 'parameters' dict; no se puede crear AzureSentinelConnectionName."
        )
        return

    workflow_name_param = None
    for pname in params.keys():
        if isinstance(pname, str) and RE_WORKFLOW_NAME.fullmatch(pname):
            workflow_name_param = pname
            break

    if workflow_name_param is None:
        logger.warning(
            "No se encontró ningún parámetro workflows_*_name. "
            "Se usará 'PlaybookName' como parámetro de nombre en AzureSentinelConnectionName."
        )
        workflow_name_param = "PlaybookName"

    variables = playbook.get("variables")
    if not isinstance(variables, dict):
        variables = {}
        playbook["variables"] = variables

    expression = (
        "[concat('azuresentinel-', parameters('"
        + workflow_name_param
        + "'))]"
    )

    variables["AzureSentinelConnectionName"] = expression

    logger.debug(
        "AzureSentinelConnectionName establecido a %s usando el parámetro '%s'.",
        expression,
        workflow_name_param,
    )


# ---------------------------------------------------------------------------
# workflows_*_externalid → variables
# ---------------------------------------------------------------------------
def _add_workflow_externalid_variables(playbook: Dict[str, Any]) -> List[str]:
    """
    Crea var_<workflows_*_externalid> con el resourceId de Microsoft.Logic/workflows.
    """
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
# connections_keyvault*_externalid → variables
# ---------------------------------------------------------------------------
def _add_connection_keyvault_externalid_variables(playbook: Dict[str, Any]) -> List[str]:
    """
    Para cada parámetro connections_keyvault.*_externalid:
      - Asegura la variable:
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
# Reemplazar [parameters()] → [variables()] para *_externalid
# ---------------------------------------------------------------------------
def _replace_parameters_with_variables(
    playbook: Dict[str, Any],
    param_names: List[str],
) -> None:
    """
    Reemplaza en todo el JSON:

      [parameters('<nombre_param>')]
    por:
      [variables('var_<nombre_param>')]
    """
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
# Bloques $connections + dependsOn usando AzureSentinelConnectionName y keyvault_Connection_Name
# ---------------------------------------------------------------------------
def _ensure_workflow_connection_blocks(playbook: Dict[str, Any]) -> None:
    """
    En cada recurso Microsoft.Logic/workflows asegura:

      properties.parameters.$connections.value = {
        "azuresentinel": { ... AzureSentinelConnectionName ... },
        "keyvault": { ... keyvault_Connection_Name ... } (solo si existe)
      }

    y añade en dependsOn:
      - [resourceId('Microsoft.Web/connections', variables('AzureSentinelConnectionName'))]
      - [resourceId('Microsoft.Web/connections', variables('keyvault_Connection_Name'))]
        (si existe la variable).
    """
    resources = playbook.get("resources", [])
    if not isinstance(resources, list):
        return

    variables = playbook.get("variables", {})
    has_azure = "AzureSentinelConnectionName" in variables
    has_kv = "keyvault_Connection_Name" in variables

    if not has_azure and not has_kv:
        return

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

        if has_azure:
            value["azuresentinel"] = {
                "connectionId": "[resourceId('Microsoft.Web/connections', variables('AzureSentinelConnectionName'))]",
                "connectionName": "[variables('AzureSentinelConnectionName')]",
                "id": "[concat('/subscriptions/', subscription().subscriptionId, '/providers/Microsoft.Web/locations/', resourceGroup().location, '/managedApis/azuresentinel')]",
                "connectionProperties": {
                    "authentication": {
                        "type": "ManagedServiceIdentity"
                    }
                }
            }
            dep_azure = "[resourceId('Microsoft.Web/connections', variables('AzureSentinelConnectionName'))]"
            if dep_azure not in depends_on:
                depends_on.append(dep_azure)

        if has_kv:
            value["keyvault"] = {
                "id": "[concat(subscription().id, '/providers/Microsoft.Web/locations/', resourceGroup().location, '/managedApis/', 'keyvault')]",
                "connectionId": "[resourceId('Microsoft.Web/connections', variables('keyvault_Connection_Name'))]",
                "connectionName": "[variables('keyvault_Connection_Name')]",
                "connectionProperties": {
                    "authentication": {
                        "type": "ManagedServiceIdentity"
                    }
                }
            }
            dep_kv = "[resourceId('Microsoft.Web/connections', variables('keyvault_Connection_Name'))]"
            if dep_kv not in depends_on:
                depends_on.append(dep_kv)


# ---------------------------------------------------------------------------
# Recursos Microsoft.Web/connections para azuresentinel y keyvault
# ---------------------------------------------------------------------------
def _ensure_connection_resources(playbook: Dict[str, Any]) -> None:
    """
    Añade (si faltan) los recursos Microsoft.Web/connections de:
      - azuresentinel (AzureSentinelConnectionName)
      - keyvault (keyvault_Connection_Name + keyvault_Name)
    """
    resources = playbook.get("resources", [])
    if not isinstance(resources, list):
        return

    variables = playbook.get("variables", {})
    params = playbook.get("parameters", {})

    has_azure = "AzureSentinelConnectionName" in variables
    has_kv = "keyvault_Connection_Name" in variables and "keyvault_Name" in params

    # Azure Sentinel connection
    if has_azure:
        azure_name_expr = "[variables('AzureSentinelConnectionName')]"
        azure_api_id_expr = (
            "[concat('/subscriptions/', subscription().subscriptionId, "
            "'/providers/Microsoft.Web/locations/', resourceGroup().location, "
            "'/managedApis/azuresentinel')]"
        )

        exists = False
        for res in resources:
            if (
                isinstance(res, dict)
                and res.get("type") == "Microsoft.Web/connections"
                and res.get("name") == azure_name_expr
            ):
                exists = True
                break

        if not exists:
            conn_resource_azure = {
                "type": "Microsoft.Web/connections",
                "apiVersion": "2016-06-01",
                "name": azure_name_expr,
                "location": "[resourceGroup().location]",
                "kind": "V1",
                "properties": {
                    "displayName": azure_name_expr,
                    "customParameterValues": {},
                    "parameterValueType": "Alternative",
                    "api": {
                        "id": azure_api_id_expr,
                    },
                },
            }
            resources.append(conn_resource_azure)

    # Key Vault connection
    if has_kv:
        kv_name_expr = "[variables('keyvault_Connection_Name')]"
        kv_api_id_expr = (
            "[concat(subscription().id, '/providers/Microsoft.Web/locations/', "
            "resourceGroup().location, '/managedApis/', 'keyvault')]"
        )

        exists_kv = False
        for res in resources:
            if (
                isinstance(res, dict)
                and res.get("type") == "Microsoft.Web/connections"
                and res.get("name") == kv_name_expr
            ):
                exists_kv = True
                break

        if not exists_kv:
            conn_resource_kv = {
                "type": "Microsoft.Web/connections",
                "apiVersion": "2016-06-01",
                "name": kv_name_expr,
                "location": "[resourceGroup().location]",
                "properties": {
                    "api": {
                        "id": kv_api_id_expr,
                    },
                    "displayName": kv_name_expr,
                    "parameterValueType": "Alternative",
                    "AlternativeParameterValues": {
                        "vaultName": "[parameters('keyvault_Name')]",
                    },
                },
            }
            resources.append(conn_resource_kv)


# ---------------------------------------------------------------------------
# Transformación principal
# ---------------------------------------------------------------------------
def transform_playbook(
    playbook: Dict[str, Any],
    master_template: Dict[str, Any],  # noqa: ARG001
) -> Dict[str, Any]:
    """
    Aplica todas las transformaciones sobre un playbook individual.
    """
    logger.debug("Iniciando transformación de playbook.")

    # 1) Siempre creamos AzureSentinelConnectionName para este playbook
    _ensure_azuresentinel_connection_name(playbook)

    # 2) Transformaciones *_externalid
    wf_params = _add_workflow_externalid_variables(playbook)
    conn_kv_params = _add_connection_keyvault_externalid_variables(playbook)

    all_params = wf_params + conn_kv_params

    if all_params:
        logger.info("Variables creadas para parámetros *_externalid: %s", all_params)
        _replace_parameters_with_variables(playbook, all_params)
    else:
        logger.debug("No se encontraron parámetros *_externalid relevantes en este playbook.")

    # 3) Bloques de conexión en los workflows (azuresentinel + keyvault)
    _ensure_workflow_connection_blocks(playbook)

    # 4) Recursos Microsoft.Web/connections al final (azuresentinel + keyvault)
    _ensure_connection_resources(playbook)

    logger.debug("Transformación completada.")
    return playbook


def run_automation(
    master_path: Path,
    dir_in: Path,
    dir_out: Path,
) -> None:
    """
    Orquesta el flujo completo para todos los playbooks referenciados en la master.
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

        inspect_workflow_parameters(playbook_data, source_name=file_name)

        transformed = transform_playbook(playbook_data, master_template)

        logger.info("Guardando playbook en el directorio de salida...")
        saved_path = write_playbook(dir_out, playbook_path, transformed)
        logger.info("Playbook guardado correctamente en: %s", saved_path)
