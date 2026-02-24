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
       * workflows_*_externalid:
           - Crea var_<workflows_*_externalid> con el resourceId del workflow.
           - Reemplaza [parameters('<param>')] por [variables('var_<param>')].
   - Manejo de conexiones:
       * Siempre crea/actualiza:
           AzureSentinelConnectionName =
             "[concat('azuresentinel-', parameters('<nombredelplaybook>'))]"
       * Si el playbook tiene algún parámetro connections_keyvault_*_externalid:
           - Crea/actualiza:
               keyvault_Connection_Name =
                 "[concat('keyvault-', parameters('<nombredelplaybook>'))]"
       * (NUEVO) En cada workflow:
           - Asegura definition.parameters.$connections (type Object + defaultValue {})
       * En cada workflow:
           - Inserta/ajusta properties.parameters.$connections.value con:
               azuresentinel (AzureSentinelConnectionName)
               keyvault (keyvault_Connection_Name), si existe.
           - Añade dependsOn a ambas conexiones si aplican.
       * Añade recursos Microsoft.Web/connections:
           - para AzureSentinelConnectionName (azuresentinel)
           - para keyvault_Connection_Name (keyvault), con AlternativeParameterValues.vaultName.
   - Además, desde la master:
       * Para cada deployment, se leen sus "properties.parameters" y cualquier
         parámetro que NO exista en el playbook se añade como:
             "<param>": {
               "type": "String",
               "defaultValue": "BORRAR_<param>"
             }
         y también en:
             resources[*].properties.definition.parameters["<param>"]
   - Y además:
       * Para cada keyvault_<Sufijo> del deployment:
           - Busca en TODO el playbook la subcadena:
               "variables('<Sufijo>')"  o  "parameters('<Sufijo>')"
           - La sustituye por:
               "parameters('keyvault_<Sufijo>')"
   - Y además (NUEVO):
       * Antes de la limpieza:
           - En cada workflow, borra entradas en $connections.value con key:
               azuresentinel-<NUMERO>  (ej: azuresentinel-1, azuresentinel-2, ...)
   - Finalmente:
       * Limpieza iterativa de parámetros no usados en el playbook:
         - Primero borra definition.parameters que no se usen fuera de definition.
         - Luego borra parámetros root que no se usen fuera de parámetros (root/definition).
         - Repite hasta que no haya más cambios.
       * Sincroniza la master:
         - Borra de properties.parameters del deployment los parámetros que ya
           no existan en el playbook resultante.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .master_loader import load_master_template
from .playbook_loader import load_playbook
from .writer import write_playbook

logger = logging.getLogger(__name__)

# Patrones regex
RE_WORKFLOW_NAME = re.compile(r"workflows_.*_name")
RE_WORKFLOW_EXTERNALID = re.compile(r"workflows_.*_externalid")
RE_CONNECTION_KEYVAULT_EXTERNALID = re.compile(r"connections_keyvault.*_externalid")

# Claves tipo "azuresentinel-1", "azuresentinel-2", ...
RE_AZURESENTINEL_NUMBERED_KEY = re.compile(r"^azuresentinel-\d+$")


# ---------------------------------------------------------------------------
# Master template helpers
# ---------------------------------------------------------------------------
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


def get_deployment_parameters_from_master(
    master_template: Dict[str, Any],
    deployment_name: str,
) -> Optional[Dict[str, Any]]:
    """
    Devuelve el diccionario properties.parameters del deployment con nombre deployment_name
    dentro de la master template, o None si no se encuentra / no es válido.
    """
    resources = master_template.get("resources", [])
    if not isinstance(resources, list):
        return None

    for res in resources:
        if not isinstance(res, dict):
            continue
        if res.get("type") != "Microsoft.Resources/deployments":
            continue
        if res.get("name") != deployment_name:
            continue

        props = res.get("properties")
        if not isinstance(props, dict):
            return None

        params = props.get("parameters")
        if isinstance(params, dict):
            return params

        return None

    return None


def _sync_master_deployment_parameters_with_playbook(
    master_template: Dict[str, Any],
    deployment_name: str,
    playbook: Dict[str, Any],
) -> None:
    """
    Sincroniza los parámetros de la master con el playbook ya transformado.

    - Para el deployment `deployment_name`:
      - Obtiene properties.parameters (p.ej. keyvault_Name, keyvault_ClientID, etc.)
      - Obtiene el conjunto de parámetros existentes en el playbook:
          * playbook["parameters"].keys()
          * resources[*].properties.definition.parameters.keys()
      - Cualquier parámetro presente en master pero que ya no exista en el playbook
        se elimina de properties.parameters del deployment.
    """
    resources = master_template.get("resources", [])
    if not isinstance(resources, list):
        return

    used_param_names: set[str] = set()

    params_root = playbook.get("parameters", {})
    if isinstance(params_root, dict):
        for pname in params_root.keys():
            if isinstance(pname, str):
                used_param_names.add(pname)

    pb_resources = playbook.get("resources", [])
    if isinstance(pb_resources, list):
        for res in pb_resources:
            if not isinstance(res, dict):
                continue
            if res.get("type") != "Microsoft.Logic/workflows":
                continue

            props = res.get("properties")
            if not isinstance(props, dict):
                continue

            definition = props.get("definition")
            if not isinstance(definition, dict):
                continue

            def_params = definition.get("parameters")
            if not isinstance(def_params, dict):
                continue

            for pname in def_params.keys():
                if isinstance(pname, str):
                    used_param_names.add(pname)

    if not used_param_names:
        return

    for res in resources:
        if not isinstance(res, dict):
            continue
        if res.get("type") != "Microsoft.Resources/deployments":
            continue
        if res.get("name") != deployment_name:
            continue

        props = res.get("properties")
        if not isinstance(props, dict):
            return

        dep_params = props.get("parameters")
        if not isinstance(dep_params, dict):
            return

        removed_any = False
        for pname in list(dep_params.keys()):
            if not isinstance(pname, str):
                continue
            if pname not in used_param_names:
                logger.debug(
                    "Eliminando parámetro '%s' de properties.parameters del deployment '%s' "
                    "porque ya no existe en el playbook.",
                    pname,
                    deployment_name,
                )
                del dep_params[pname]
                removed_any = True

        if removed_any:
            logger.info(
                "Sincronizados parámetros del deployment '%s' en la master (se eliminaron no usados).",
                deployment_name,
            )
        return


# ---------------------------------------------------------------------------
# Inspección
# ---------------------------------------------------------------------------
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
# Helpers: nombre del playbook + detección de keyvault externalid
# ---------------------------------------------------------------------------
def _get_workflow_name_param(playbook: Dict[str, Any]) -> str:
    """
    Devuelve el nombre del parámetro que representa el nombre del playbook:
      - primer workflows_*_name que encuentre
      - o 'PlaybookName' como fallback.
    """
    params = playbook.get("parameters", {})
    if not isinstance(params, dict):
        return "PlaybookName"

    for pname in params.keys():
        if isinstance(pname, str) and RE_WORKFLOW_NAME.fullmatch(pname):
            return pname

    logger.warning(
        "No se encontró ningún parámetro workflows_*_name. "
        "Se usará 'PlaybookName' como parámetro de nombre de playbook."
    )
    return "PlaybookName"


def _has_keyvault_externalid(playbook: Dict[str, Any]) -> bool:
    """
    Indica si el playbook tiene algún parámetro connections_keyvault_*_externalid.
    """
    params = playbook.get("parameters", {})
    if not isinstance(params, dict):
        return False

    for key in params.keys():
        if isinstance(key, str) and RE_CONNECTION_KEYVAULT_EXTERNALID.fullmatch(key):
            return True
    return False


# ---------------------------------------------------------------------------
# AzureSentinelConnectionName por playbook
# ---------------------------------------------------------------------------
def _ensure_azuresentinel_connection_name(playbook: Dict[str, Any]) -> None:
    """
    Para cada playbook asegura que exista la variable:

      AzureSentinelConnectionName =
        "[concat('azuresentinel-', parameters('<nombredelplaybook>'))]"
    """
    workflow_name_param = _get_workflow_name_param(playbook)

    variables = playbook.get("variables")
    if not isinstance(variables, dict):
        variables = {}
        playbook["variables"] = variables

    expression = "[concat('azuresentinel-', parameters('" + workflow_name_param + "'))]"
    variables["AzureSentinelConnectionName"] = expression

    logger.debug(
        "AzureSentinelConnectionName establecido a %s usando el parámetro '%s'.",
        expression,
        workflow_name_param,
    )


# ---------------------------------------------------------------------------
# keyvault_Connection_Name por playbook (si hay keyvault externalid)
# ---------------------------------------------------------------------------
def _ensure_keyvault_connection_name(playbook: Dict[str, Any]) -> None:
    """
    Si el playbook usa connections_keyvault_*_externalid, asegura que exista:

      keyvault_Connection_Name =
        "[concat('keyvault-', parameters('<nombredelplaybook>'))]"
    """
    if not _has_keyvault_externalid(playbook):
        return

    workflow_name_param = _get_workflow_name_param(playbook)

    variables = playbook.get("variables")
    if not isinstance(variables, dict):
        variables = {}
        playbook["variables"] = variables

    expression = "[concat('keyvault-', parameters('" + workflow_name_param + "'))]"
    variables["keyvault_Connection_Name"] = expression

    logger.debug(
        "keyvault_Connection_Name establecido a %s usando el parámetro '%s'.",
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
# Reemplazar [parameters()] → [variables()] para *_externalid (solo workflows)
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
# NUEVO: asegurar definition.parameters.$connections en todos los workflows
# ---------------------------------------------------------------------------
def _ensure_definition_connections_parameter(playbook: Dict[str, Any]) -> None:
    """
    Asegura que cada workflow tenga:
      properties.definition.parameters.$connections = { "type": "Object", "defaultValue": {} }
    """
    resources = playbook.get("resources", [])
    if not isinstance(resources, list):
        return

    for res in resources:
        if not isinstance(res, dict):
            continue
        if res.get("type") != "Microsoft.Logic/workflows":
            continue

        props = res.get("properties")
        if not isinstance(props, dict):
            continue

        definition = props.get("definition")
        if not isinstance(definition, dict):
            continue

        def_params = definition.get("parameters")
        if not isinstance(def_params, dict):
            def_params = {}
            definition["parameters"] = def_params

        if "$connections" not in def_params or not isinstance(def_params.get("$connections"), dict):
            def_params["$connections"] = {"type": "Object", "defaultValue": {}}
        else:
            def_params["$connections"].setdefault("type", "Object")
            def_params["$connections"].setdefault("defaultValue", {})



def _replace_numbered_azuresentinel_in_body(playbook: Dict[str, Any]) -> None:
    def _walk(obj: Any) -> Any:
        if isinstance(obj, str):
            return re.sub(r"\['azuresentinel-\d+'\]", "['azuresentinel']", obj)
        if isinstance(obj, dict):
            for k, v in obj.items():
                obj[k] = _walk(v)
            return obj
        if isinstance(obj, list):
            for i, v in enumerate(obj):
                obj[i] = _walk(v)
            return obj
        return obj

    _walk(playbook)
    logger.debug("Reemplazadas referencias 'azuresentinel-<n>' por 'azuresentinel' en el body.")

    
# ---------------------------------------------------------------------------
# NUEVO: quitar conexiones "azuresentinel-<numero>" del $connections.value
# ---------------------------------------------------------------------------
def _remove_numbered_azuresentinel_connections(playbook: Dict[str, Any]) -> None:
    """
    En cada workflow, elimina entradas del bloque:
      properties.parameters.$connections.value
    cuyas keys sean: azuresentinel-<NUMERO> (ej: azuresentinel-1).
    """
    resources = playbook.get("resources", [])
    if not isinstance(resources, list):
        return

    removed_total = 0

    for res in resources:
        if not isinstance(res, dict):
            continue
        if res.get("type") != "Microsoft.Logic/workflows":
            continue

        props = res.get("properties")
        if not isinstance(props, dict):
            continue

        parameters = props.get("parameters")
        if not isinstance(parameters, dict):
            continue

        connections = parameters.get("$connections")
        if not isinstance(connections, dict):
            continue

        value = connections.get("value")
        if not isinstance(value, dict) or not value:
            continue

        for k in list(value.keys()):
            # 🔹 AÑADIDO: limpieza explícita de azuresentinel-<n>
            if (
                isinstance(k, str)
                and RE_AZURESENTINEL_NUMBERED_KEY.fullmatch(k)
            ):
                del value[k]
                removed_total += 1

    if removed_total:
        logger.info(
            "Eliminadas %d entradas $connections.value tipo 'azuresentinel-<n>'.",
            removed_total,
        )
    
    _replace_numbered_azuresentinel_in_body(playbook)

# ---------------------------------------------------------------------------
# Bloques $connections + dependsOn usando AzureSentinelConnectionName y keyvault_Connection_Name
# ---------------------------------------------------------------------------
def _ensure_workflow_connection_blocks(playbook: Dict[str, Any]) -> None:
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
                "connectionProperties": {"authentication": {"type": "ManagedServiceIdentity"}},
            }
            dep_azure = "[resourceId('Microsoft.Web/connections', variables('AzureSentinelConnectionName'))]"
            if dep_azure not in depends_on:
                depends_on.append(dep_azure)

        if has_kv:
            value["keyvault"] = {
                "id": "[concat(subscription().id, '/providers/Microsoft.Web/locations/', resourceGroup().location, '/managedApis/', 'keyvault')]",
                "connectionId": "[resourceId('Microsoft.Web/connections', variables('keyvault_Connection_Name'))]",
                "connectionName": "[variables('keyvault_Connection_Name')]",
                "connectionProperties": {"authentication": {"type": "ManagedServiceIdentity"}},
            }
            dep_kv = "[resourceId('Microsoft.Web/connections', variables('keyvault_Connection_Name'))]"
            if dep_kv not in depends_on:
                depends_on.append(dep_kv)


# ---------------------------------------------------------------------------
# Recursos Microsoft.Web/connections para azuresentinel y keyvault
# ---------------------------------------------------------------------------
def _ensure_connection_resources(playbook: Dict[str, Any]) -> None:
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
            resources.append(
                {
                    "type": "Microsoft.Web/connections",
                    "apiVersion": "2016-06-01",
                    "name": azure_name_expr,
                    "location": "[resourceGroup().location]",
                    "kind": "V1",
                    "properties": {
                        "displayName": azure_name_expr,
                        "customParameterValues": {},
                        "parameterValueType": "Alternative",
                        "api": {"id": azure_api_id_expr},
                    },
                }
            )

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
            resources.append(
                {
                    "type": "Microsoft.Web/connections",
                    "apiVersion": "2016-06-01",
                    "name": kv_name_expr,
                    "location": "[resourceGroup().location]",
                    "properties": {
                        "api": {"id": kv_api_id_expr},
                        "displayName": kv_name_expr,
                        "parameterValueType": "Alternative",
                        "AlternativeParameterValues": {"vaultName": "[parameters('keyvault_Name')]"},
                    },
                }
            )


# ---------------------------------------------------------------------------
# Merge de parámetros de la master hacia el playbook
# ---------------------------------------------------------------------------
def _merge_deployment_parameters_into_playbook(
    playbook: Dict[str, Any],
    deployment_params: Optional[Dict[str, Any]],
) -> None:
    if not deployment_params or not isinstance(deployment_params, dict):
        return

    params = playbook.get("parameters")
    if not isinstance(params, dict):
        params = {}
        playbook["parameters"] = params

    resources = playbook.get("resources", [])
    if not isinstance(resources, list):
        resources = []

    for pname in deployment_params.keys():
        if pname not in params:
            entry: Dict[str, Any] = {"type": "String", "defaultValue": f"BORRAR_{pname}"}
            params[pname] = entry
            logger.debug("Añadido parámetro root desde master al playbook: %s -> %r", pname, entry)

        for res in resources:
            if not isinstance(res, dict):
                continue
            if res.get("type") != "Microsoft.Logic/workflows":
                continue

            props = res.get("properties")
            if not isinstance(props, dict):
                props = {}
                res["properties"] = props

            definition = props.get("definition")
            if not isinstance(definition, dict):
                continue

            def_params = definition.get("parameters")
            if not isinstance(def_params, dict):
                def_params = {}
                definition["parameters"] = def_params

            if pname in def_params:
                continue

            def_entry: Dict[str, Any] = {"type": "String", "defaultValue": f"[parameters('{pname}')]"}

            def_params[pname] = def_entry
            logger.debug(
                "Añadido parámetro definition.parameters desde master al playbook: %s -> %r",
                pname,
                def_entry,
            )


# ---------------------------------------------------------------------------
# KeyVault: reemplazar variables('<Sufijo>') Y parameters('<Sufijo>') por parameters('keyvault_<Sufijo>')
# ---------------------------------------------------------------------------
def _replace_keyvault_variable_references(
    playbook: Dict[str, Any],
    deployment_params: Optional[Dict[str, Any]],
) -> None:
    if not deployment_params or not isinstance(deployment_params, dict):
        return

    replacements: Dict[str, str] = {}

    for pname in deployment_params.keys():
        if not isinstance(pname, str):
            continue
        if not pname.startswith("keyvault_"):
            continue

        suffix = pname[len("keyvault_") :]
        if not suffix:
            continue

        replacements[f"variables('{suffix}')"] = f"parameters('{pname}')"

        if not suffix.startswith("keyvault_"):
            replacements[f"parameters('{suffix}')"] = f"parameters('{pname}')"

    if not replacements:
        return

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

    logger.debug(
        "Reemplazadas referencias variables/parameters('<Sufijo>') por parameters('keyvault_<Sufijo>'): %s",
        replacements,
    )


# ---------------------------------------------------------------------------
# Limpieza iterativa de parámetros no usados
# ---------------------------------------------------------------------------
def _remove_unused_definition_parameters(playbook: Dict[str, Any]) -> bool:
    resources = playbook.get("resources", [])
    if not isinstance(resources, list) or not resources:
        return False

    stripped = json.loads(json.dumps(playbook))
    stripped_resources = stripped.get("resources", [])
    if isinstance(stripped_resources, list):
        for res in stripped_resources:
            if isinstance(res, dict) and res.get("type") == "Microsoft.Logic/workflows":
                props = res.get("properties")
                if not isinstance(props, dict):
                    continue
                definition = props.get("definition")
                if isinstance(definition, dict) and "parameters" in definition:
                    del definition["parameters"]

    stripped_str = json.dumps(stripped)
    changed = False

    for res in resources:
        if not isinstance(res, dict):
            continue
        if res.get("type") != "Microsoft.Logic/workflows":
            continue

        props = res.get("properties")
        if not isinstance(props, dict):
            continue

        definition = props.get("definition")
        if not isinstance(definition, dict):
            continue

        def_params = definition.get("parameters")
        if not isinstance(def_params, dict) or not def_params:
            continue

        for pname in list(def_params.keys()):
            if not isinstance(pname, str):
                continue
            pattern = f"parameters('{pname}')"
            if pattern in stripped_str:
                continue

            logger.debug("Parámetro definition.parameters no usado detectado. Se eliminará: %s", pname)
            del def_params[pname]
            changed = True

    return changed


def _remove_unused_root_parameters(playbook: Dict[str, Any]) -> bool:
    params_root = playbook.get("parameters")
    if not isinstance(params_root, dict) or not params_root:
        return False

    stripped = json.loads(json.dumps(playbook))

    if "parameters" in stripped:
        del stripped["parameters"]

    stripped_resources = stripped.get("resources", [])
    if isinstance(stripped_resources, list):
        for res in stripped_resources:
            if isinstance(res, dict) and res.get("type") == "Microsoft.Logic/workflows":
                props = res.get("properties")
                if not isinstance(props, dict):
                    continue
                definition = props.get("definition")
                if isinstance(definition, dict) and "parameters" in definition:
                    del definition["parameters"]

    stripped_str = json.dumps(stripped)
    changed = False

    for pname in list(params_root.keys()):
        if not isinstance(pname, str):
            continue

        pattern = f"parameters('{pname}')"
        if pattern in stripped_str:
            continue

        logger.debug("Parámetro root no usado detectado. Se eliminará: %s", pname)
        del params_root[pname]
        changed = True

    return changed


def _cleanup_unused_parameters(playbook: Dict[str, Any]) -> None:
    while True:
        changed_def = _remove_unused_definition_parameters(playbook)
        changed_root = _remove_unused_root_parameters(playbook)
        if not (changed_def or changed_root):
            break

def _sanitize_workflow_parameters(playbook: Dict[str, Any]) -> None:
    """
    Sanitizes only root parameters whose name starts with 'workflows_'.

    Rule:
      - parameters["workflows_*"].defaultValue (string) -> "BORRAR"
      - Everything else remains untouched
    """
    params = playbook.get("parameters")
    if not isinstance(params, dict):
        return

    for pname, pdef in params.items():
        if not isinstance(pname, str):
            continue
        if not pname.startswith("workflows_"):
            continue
        if not isinstance(pdef, dict):
            continue
        if isinstance(pdef.get("defaultValue"), str):
            pdef["defaultValue"] = "BORRAR"

# ---------------------------------------------------------------------------
# Transformación principal
# ---------------------------------------------------------------------------
def transform_playbook(
    playbook: Dict[str, Any],
    deployment_parameters: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    logger.debug("Iniciando transformación de playbook.")

    _merge_deployment_parameters_into_playbook(playbook, deployment_parameters)
    _replace_keyvault_variable_references(playbook, deployment_parameters)

    _ensure_azuresentinel_connection_name(playbook)
    _ensure_keyvault_connection_name(playbook)

    wf_params = _add_workflow_externalid_variables(playbook)
    if wf_params:
        logger.info("Variables creadas para parámetros *_externalid (workflows): %s", wf_params)
        _replace_parameters_with_variables(playbook, wf_params)
    else:
        logger.debug("No se encontraron parámetros workflows_*_externalid en este playbook.")

    _remove_numbered_azuresentinel_connections(playbook)

    # Final step: sanitize only workflows_* root parameters
    _sanitize_workflow_parameters(playbook)

    _ensure_workflow_connection_blocks(playbook)
    _ensure_connection_resources(playbook)

    _cleanup_unused_parameters(playbook)
    _ensure_definition_connections_parameter(playbook)

    logger.debug("Transformación completada.")
    return playbook


# ---------------------------------------------------------------------------
# Orquestador
# ---------------------------------------------------------------------------
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
        candidate_paths = [
            dir_in / f"Cliente_{name}.json",
            dir_in / f"{name}.json",
        ]

        playbook_path = next((p for p in candidate_paths if p.is_file()), None)

        if playbook_path is None:
            logger.warning(
                "No se encontró el playbook esperado (Cliente_%s.json ni %s.json) en: %s",
                name,
                name,
                dir_in,
            )
            continue

        logger.info("Leyendo playbook: %s", playbook_path)
        playbook_data = load_playbook(playbook_path)

        deployment_params = get_deployment_parameters_from_master(master_template, name)

        inspect_workflow_parameters(playbook_data, source_name=playbook_path.name)

        transformed = transform_playbook(playbook_data, deployment_params)

        _sync_master_deployment_parameters_with_playbook(master_template, name, transformed)

        logger.info("Guardando playbook en el directorio de salida...")
        saved_path = write_playbook(dir_out, playbook_path, transformed)
        logger.info("Playbook guardado correctamente en: %s", saved_path)

    logger.info("Guardando master template transformada en el directorio de salida...")
    saved_master = write_playbook(dir_out, master_path, master_template)
    logger.info("Master template guardada en: %s", saved_master)
