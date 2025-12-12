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
               "variables('<Sufijo>')"
           - La sustituye por:
               "parameters('keyvault_<Sufijo>')"
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

import logging
import re
import json
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

    # Conjunto de parámetros que siguen existiendo en el playbook
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
        # Si no hay parámetros en el playbook, no tocamos la master
        return

    # Localizamos el deployment correspondiente en la master
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

    expression = (
        "[concat('keyvault-', parameters('"
        + workflow_name_param
        + "'))]"
    )

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
# Merge de parámetros de la master hacia el playbook
# ---------------------------------------------------------------------------
def _merge_deployment_parameters_into_playbook(
    playbook: Dict[str, Any],
    deployment_params: Optional[Dict[str, Any]],
) -> None:
    """
    Toma los parámetros definidos en el deployment de la master (properties.parameters)
    y añade al playbook cualquier parámetro que no exista aún, con:

      "<param>": {
        "type": "String",
        "defaultValue": "BORRAR_<param>"
      }

    Y también los añade en:
      resources[*].properties.definition.parameters["<param>"]
    con el mismo esquema.
    """
    if not deployment_params or not isinstance(deployment_params, dict):
        return

    # 1) Root parameters del playbook
    params = playbook.get("parameters")
    if not isinstance(params, dict):
        params = {}
        playbook["parameters"] = params

    # 2) Definition.parameters de cada workflow
    resources = playbook.get("resources", [])
    if not isinstance(resources, list):
        resources = []

    for pname in deployment_params.keys():
        # --- root-level parameters ---
        if pname not in params:
            entry: Dict[str, Any] = {
                "type": "String",
                "defaultValue": f"BORRAR_{pname}",
            }
            params[pname] = entry
            logger.debug(
                "Añadido parámetro root desde master al playbook: %s -> %r",
                pname,
                entry,
            )

        # --- definition.parameters en cada workflow ---
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
                # si no hay definición de workflow, no hacemos nada aquí
                continue

            def_params = definition.get("parameters")
            if not isinstance(def_params, dict):
                def_params = {}
                definition["parameters"] = def_params

            if pname in def_params:
                continue

            def_entry: Dict[str, Any] = {
                "type": "String",
                "defaultValue": f"[parameters('{pname}')]",
            }
            def_params[pname] = def_entry

            logger.debug(
                "Añadido parámetro definition.parameters desde master al playbook: %s -> %r",
                pname,
                def_entry,
            )


# ---------------------------------------------------------------------------
# KeyVault: reemplazar variables('<Sufijo>') por parameters('keyvault_<Sufijo>')
# ---------------------------------------------------------------------------
def _replace_keyvault_variable_references(
    playbook: Dict[str, Any],
    deployment_params: Optional[Dict[str, Any]],
) -> None:
    """
    Para cada parámetro keyvault_<Sufijo> definido en el deployment de la master,
    recorre TODO el playbook y reemplaza:

      "variables('<Sufijo>')"

    por:

      "parameters('keyvault_<Sufijo>')"
    """
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

        old = f"variables('{suffix}')"
        new = f"parameters('{pname}')"
        replacements[old] = new

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
        "Reemplazadas referencias variables('<Sufijo>') por parameters('keyvault_<Sufijo>'): %s",
        replacements,
    )


# ---------------------------------------------------------------------------
# Limpieza iterativa de parámetros no usados
# ---------------------------------------------------------------------------
def _remove_unused_definition_parameters(playbook: Dict[str, Any]) -> bool:
    """
    Borra parámetros dentro de definition.parameters que no se usan en ningún
    sitio fuera de los propios bloques definition.parameters.

    Estrategia:
      - Hacemos una copia del playbook y le eliminamos TODOS los
        definition.parameters.
      - Serializamos esa copia a JSON (stripped_str).
      - Si en stripped_str NO aparece "parameters('<pname>')", se considera
        que ese parámetro solo vive en definition.parameters → se elimina.
    """
    resources = playbook.get("resources", [])
    if not isinstance(resources, list) or not resources:
        return False

    # Copia profunda del playbook para quitar definition.parameters
    stripped = json.loads(json.dumps(playbook))
    stripped_resources = stripped.get("resources", [])
    if isinstance(stripped_resources, list):
        for res in stripped_resources:
            if (
                isinstance(res, dict)
                and res.get("type") == "Microsoft.Logic/workflows"
            ):
                props = res.get("properties")
                if not isinstance(props, dict):
                    continue
                definition = props.get("definition")
                if isinstance(definition, dict) and "parameters" in definition:
                    del definition["parameters"]

    stripped_str = json.dumps(stripped)
    changed = False

    # Ahora iteramos sobre los definition.parameters reales y vemos si se usan
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
                # Se usa fuera de definition.parameters → lo dejamos
                continue

            # No se usa fuera de definition.parameters → lo eliminamos
            logger.debug(
                "Parámetro definition.parameters no usado detectado. Se eliminará: %s",
                pname,
            )
            del def_params[pname]
            changed = True

    return changed


def _remove_unused_root_parameters(playbook: Dict[str, Any]) -> bool:
    """
    Borra parámetros root (playbook['parameters']) que no se usan en ningún
    sitio fuera de playbook['parameters'] ni de definition.parameters.

    Estrategia:
      - Copia del playbook sin:
          * playbook['parameters']
          * todos los definition.parameters
      - Serializar esa copia y buscar "parameters('<pname>')" ahí.
      - Si NO aparece, se considera no usado y se borra del root.
    """
    params_root = playbook.get("parameters")
    if not isinstance(params_root, dict) or not params_root:
        return False

    # Copia profunda del playbook para quitar root parameters y definition.parameters
    stripped = json.loads(json.dumps(playbook))

    # Eliminar parámetros root
    if "parameters" in stripped:
        del stripped["parameters"]

    stripped_resources = stripped.get("resources", [])
    if isinstance(stripped_resources, list):
        for res in stripped_resources:
            if (
                isinstance(res, dict)
                and res.get("type") == "Microsoft.Logic/workflows"
            ):
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
            # Se usa en el cuerpo del workflow (acciones, expresiones, etc.) → lo dejamos
            continue

        logger.debug(
            "Parámetro root no usado detectado. Se eliminará: %s",
            pname,
        )
        del params_root[pname]
        changed = True

    return changed


def _cleanup_unused_parameters(playbook: Dict[str, Any]) -> None:
    """
    Ejecuta limpieza iterativa:
      1) Borrar definition.parameters no usados.
      2) Borrar parámetros root no usados.
    Repite hasta que en una iteración completa no se borre nada.
    """
    while True:
        changed_def = _remove_unused_definition_parameters(playbook)
        changed_root = _remove_unused_root_parameters(playbook)

        if not (changed_def or changed_root):
            break


# ---------------------------------------------------------------------------
# Transformación principal
# ---------------------------------------------------------------------------
def transform_playbook(
    playbook: Dict[str, Any],
    deployment_parameters: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Aplica todas las transformaciones sobre un playbook individual.

    - Fusiona los parámetros del deployment de la master (properties.parameters)
      añadiendo al playbook los que falten (root + definition.parameters).
    - Reemplaza variables('<Sufijo>') por parameters('keyvault_<Sufijo>') para keyvault_*.
    - Aplica la lógica de variables y conexiones.
    - Limpia parámetros no usados de forma iterativa.
    """
    logger.debug("Iniciando transformación de playbook.")

    # 0) Fusionar parámetros de la master → playbook
    _merge_deployment_parameters_into_playbook(playbook, deployment_parameters)

    # 1) Reemplazar variables('ClientID') / variables('ClientSecret') / ... por parameters('keyvault_*')
    _replace_keyvault_variable_references(playbook, deployment_parameters)

    # 2) Variables de nombre de conexión por playbook
    _ensure_azuresentinel_connection_name(playbook)
    _ensure_keyvault_connection_name(playbook)

    # 3) Transformaciones *_externalid (solo workflows_*_externalid)
    wf_params = _add_workflow_externalid_variables(playbook)
    all_params = wf_params

    if all_params:
        logger.info("Variables creadas para parámetros *_externalid (workflows): %s", all_params)
        _replace_parameters_with_variables(playbook, all_params)
    else:
        logger.debug("No se encontraron parámetros workflows_*_externalid en este playbook.")

    # 4) Bloques de conexión en los workflows (azuresentinel + keyvault)
    _ensure_workflow_connection_blocks(playbook)

    # 5) Recursos Microsoft.Web/connections al final (azuresentinel + keyvault)
    _ensure_connection_resources(playbook)

    # 6) Limpieza iterativa de parámetros no usados
    _cleanup_unused_parameters(playbook)

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
    """
    Orquesta el flujo completo para todos los playbooks referenciados en la master.
    Además, sincroniza y guarda una versión limpia de la master en dir_out.
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

        # Parámetros específicos del deployment en la master
        deployment_params = get_deployment_parameters_from_master(master_template, name)

        # Mostrar por pantalla los parámetros de interés usando el nombre real del fichero
        inspect_workflow_parameters(playbook_data, source_name=playbook_path.name)

        transformed = transform_playbook(playbook_data, deployment_params)

        # Sincronizar parámetros de la master para este deployment según el playbook resultante
        _sync_master_deployment_parameters_with_playbook(
            master_template,
            name,
            transformed,
        )

        logger.info("Guardando playbook en el directorio de salida...")
        saved_path = write_playbook(dir_out, playbook_path, transformed)
        logger.info("Playbook guardado correctamente en: %s", saved_path)

    # Guardar también la master template transformada/limpia en dir_out
    logger.info("Guardando master template transformada en el directorio de salida...")
    saved_master = write_playbook(dir_out, master_path, master_template)
    logger.info("Master template guardada en: %s", saved_master)
