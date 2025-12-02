import argparse
import json
import sys
from typing import Dict, Any, Set, Optional, List

from .core import replace_literals, replace_substrings, add_parameter_definitions


# ---------------------------------------------------------------------
# Extracción de candidatos como en la GUI
# ---------------------------------------------------------------------


def extract_literal_candidates_from_params_and_variables(
    template: Dict[str, Any]
) -> Dict[str, Dict[str, Any]]:
    """
    Escanea el template ARM y devuelve:
        {
          "<literal>": {
              "used_in": [ "ARM parameter 'X'", "Variable 'Y' (action 'Z')" ],
              "suggested_param": "nombre_parametro_sugerido"
          },
          ...
        }
    """
    candidates: Dict[str, Dict[str, Any]] = {}

    # 1) Parámetros ARM del root
    params = template.get("parameters", {})
    if isinstance(params, dict):
        for pname, pdef in params.items():
            if not isinstance(pdef, dict):
                continue
            lit = pdef.get("defaultValue")
            if not isinstance(lit, str):
                continue

            entry = candidates.setdefault(
                lit,
                {"used_in": [], "suggested_param": pname},
            )
            entry["used_in"].append(f"ARM parameter '{pname}'")
            if not entry.get("suggested_param"):
                entry["suggested_param"] = pname

    # 2) Variables Logic Apps (InitializeVariable)
    resources = template.get("resources", [])
    if isinstance(resources, list):
        for res in resources:
            if not isinstance(res, dict):
                continue
            if res.get("type") != "Microsoft.Logic/workflows":
                continue

            props = res.get("properties") or {}
            definition = props.get("definition") or {}
            actions = definition.get("actions") or {}
            if not isinstance(actions, dict):
                continue

            for action_name, action in actions.items():
                if not isinstance(action, dict):
                    continue
                if action.get("type") != "InitializeVariable":
                    continue

                inputs = action.get("inputs") or {}
                vars_list = inputs.get("variables") or []
                if not isinstance(vars_list, list):
                    continue

                for var in vars_list:
                    if not isinstance(var, dict):
                        continue
                    vname = var.get("name")
                    vtype = var.get("type")
                    vval = var.get("value")

                    if vtype != "string" or not isinstance(vval, str):
                        continue

                    literal = vval
                    where = f"Variable '{vname}' (action '{action_name}')"

                    entry = candidates.setdefault(
                        literal,
                        {"used_in": [], "suggested_param": vname or ""},
                    )
                    entry["used_in"].append(where)

                    if not entry.get("suggested_param") and vname:
                        entry["suggested_param"] = vname

    # 3) Limpiar nombres sugeridos
    for lit, info in candidates.items():
        pname = info.get("suggested_param") or ""
        pname = pname.strip().replace(" ", "_").replace("-", "_").replace("/", "_")
        if not pname:
            pname = "param"
        if not pname[0].isalpha():
            pname = "p_" + pname
        info["suggested_param"] = pname[:80]

    return candidates


# ---------------------------------------------------------------------
# Utilidades de soporte (variables, conexiones, etc.)
# ---------------------------------------------------------------------


def uses_keyvault_connection(template: Dict[str, Any]) -> bool:
    """Devuelve True si el template usa algo relacionado con Key Vault."""
    try:
        dumped = json.dumps(template).lower()
    except TypeError:
        return False
    return "keyvault" in dumped


def ensure_default_variables(
    template: Dict[str, Any],
    playbook_param_name: Optional[str] = None
) -> None:
    """
    Asegura que en template['variables'] existan:
      - AzureSentinelConnectionName
      - keyvault_Connection_Name (solo si se detecta uso de Key Vault)
    """
    if not playbook_param_name:
        playbook_param_name = "PlaybookName"

    variables = template.setdefault("variables", {})

    variables["AzureSentinelConnectionName"] = (
        f"[concat('azuresentinel-', parameters('{playbook_param_name}'))]"
    )

    if uses_keyvault_connection(template):
        variables["keyvault_Connection_Name"] = (
            f"[concat('keyvault-', parameters('{playbook_param_name}'))]"
        )


def ensure_connections_blocks(template: Dict[str, Any]) -> None:
    """
    Asegura que en cada workflow exista:

      properties.parameters.$connections.value.azuresentinel / keyvault

    y crea/ajusta dependsOn:
      - AzureSentinelConnectionName (siempre)
      - keyvault_Connection_Name (si se usa Key Vault)
    """
    keyvault_used = uses_keyvault_connection(template)

    resources = template.get("resources", [])
    if not isinstance(resources, list):
        return

    for res in resources:
        if not isinstance(res, dict):
            continue
        if res.get("type") != "Microsoft.Logic/workflows":
            continue

        props = res.setdefault("properties", {})
        wf_params = props.setdefault("parameters", {})
        connections = wf_params.setdefault("$connections", {})
        value = connections.setdefault("value", {})

        # azuresentinel
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

        # keyvault
        if keyvault_used:
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
        else:
            if "keyvault" in value:
                del value["keyvault"]

        connections["value"] = value

        # dependsOn
        az_dep = "[resourceId('Microsoft.Web/connections', variables('AzureSentinelConnectionName'))]"
        kv_dep = "[resourceId('Microsoft.Web/connections', variables('keyvault_Connection_Name'))]"

        depends_on = res.get("dependsOn")
        if not isinstance(depends_on, list):
            depends_on = []

        new_depends = []
        for d in depends_on:
            if not isinstance(d, str):
                new_depends.append(d)
                continue
            if d in (az_dep, kv_dep):
                continue
            new_depends.append(d)

        if az_dep not in new_depends:
            new_depends.append(az_dep)
        if keyvault_used and kv_dep not in new_depends:
            new_depends.append(kv_dep)

        res["dependsOn"] = new_depends


def ensure_connection_resources(
    template: Dict[str, Any],
    keyvault_param_name: Optional[str] = None
) -> None:
    """
    Asegura que existan los recursos 'Microsoft.Web/connections' para:
      - AzureSentinelConnectionName
      - keyvault_Connection_Name (solo si se usa Key Vault)
    """
    resources = template.setdefault("resources", [])
    if not isinstance(resources, list):
        return

    keyvault_used = uses_keyvault_connection(template)
    if not keyvault_param_name:
        keyvault_param_name = "keyvault_Name"

    az_name_expr = "[variables('AzureSentinelConnectionName')]"
    kv_name_expr = "[variables('keyvault_Connection_Name')]"

    az_exists = False
    kv_exists = False

    for res in resources:
        if not isinstance(res, dict):
            continue
        if res.get("type") != "Microsoft.Web/connections":
            continue
        name = res.get("name")
        if name == az_name_expr:
            az_exists = True
        if name == kv_name_expr:
            kv_exists = True

    # Azure Sentinel
    if not az_exists:
        resources.append(
            {
                "type": "Microsoft.Web/connections",
                "apiVersion": "2016-06-01",
                "name": az_name_expr,
                "location": "[resourceGroup().location]",
                "kind": "V1",
                "properties": {
                    "displayName": az_name_expr,
                    "customParameterValues": {},
                    "parameterValueType": "Alternative",
                    "api": {
                        "id": "[concat('/subscriptions/', subscription().subscriptionId, '/providers/Microsoft.Web/locations/', resourceGroup().location, '/managedApis/azuresentinel')]"
                    }
                }
            }
        )

    # Key Vault
    if keyvault_used and not kv_exists:
        resources.append(
            {
                "type": "Microsoft.Web/connections",
                "apiVersion": "2016-06-01",
                "name": kv_name_expr,
                "location": "[resourceGroup().location]",
                "properties": {
                    "api": {
                        "id": "[concat(subscription().id, '/providers/Microsoft.Web/locations/', resourceGroup().location, '/managedApis/', 'keyvault')]"
                    },
                    "displayName": kv_name_expr,
                    "parameterValueType": "Alternative",
                    "AlternativeParameterValues": {
                        "vaultName": f"[parameters('{keyvault_param_name}')]"
                    }
                }
            }
        )


def overwrite_parameter_defaults_with_names(template: Dict[str, Any]) -> None:
    """defaultValue = nombre del parámetro para todos los String."""
    params = template.get("parameters", {})
    if not isinstance(params, dict):
        return

    for pname, pdef in params.items():
        if not isinstance(pdef, dict):
            continue
        ptype = pdef.get("type")
        if isinstance(ptype, str) and ptype.lower() == "string":
            pdef["defaultValue"] = pname


def keep_only_selected_parameters(
    template: Dict[str, Any],
    selected_param_names: Set[str]
) -> None:
    """Deja en template['parameters'] solo los nombres indicados."""
    params = template.get("parameters", {})
    if not isinstance(params, dict):
        return

    new_params = {
        pname: pdef
        for pname, pdef in params.items()
        if pname in selected_param_names
    }
    template["parameters"] = new_params


def ensure_definition_parameters(template: Dict[str, Any]) -> None:
    """
    Mete todos los parámetros de template['parameters'] dentro de
    properties.definition.parameters de cada workflow:

      "<pname>": {
        "type": "...",
        "defaultValue": "[parameters('<pname>')]"
      }
    """
    params = template.get("parameters", {})
    if not isinstance(params, dict) or not params:
        return

    resources = template.get("resources", [])
    if not isinstance(resources, list):
        return

    for res in resources:
        if not isinstance(res, dict):
            continue
        if res.get("type") != "Microsoft.Logic/workflows":
            continue

        props = res.setdefault("properties", {})
        definition = props.setdefault("definition", {})
        def_params = definition.setdefault("parameters", {})

        for pname, pdef in params.items():
            if not isinstance(pdef, dict):
                continue
            if pname in def_params:
                continue

            ptype = pdef.get("type", "String")
            if not isinstance(ptype, str):
                ptype = "String"

            def_params[pname] = {
                "type": ptype,
                "defaultValue": f"[parameters('{pname}')]"
            }


def ensure_externalid_suffix(name: str) -> str:
    """
    Garantiza que el nombre termine en _externalid (case-insensitive).
    """
    low = name.lower()
    if low.endswith("_externalid"):
        return name
    if low.endswith("externalid"):
        return name
    return f"{name}_externalid"


def set_externalid_defaults(
    template: Dict[str, Any],
    externalid_param_names: Set[str],
    playbook_param_name: Optional[str]
) -> None:
    """
    Pone en cada parámetro *_externalid el defaultValue con el concat(...)
    al workflow del playbook.
    """
    if not externalid_param_names:
        return

    if not playbook_param_name:
        playbook_param_name = "PlaybookName"

    params = template.get("parameters", {})
    if not isinstance(params, dict):
        return

    concat_expr = (
        f"[concat('/subscriptions/', subscription().subscriptionId, "
        f"'/resourceGroups/', resourceGroup().name ,"
        f"'/providers/Microsoft.Logic/workflows/', parameters('{playbook_param_name}'))]"
    )

    for pname, pdef in params.items():
        if pname in externalid_param_names and isinstance(pdef, dict):
            pdef["type"] = pdef.get("type", "String")
            pdef["defaultValue"] = concat_expr


# ---------------------------------------------------------------------
# Parametrización guiada por TIPOS, usando candidatos GUI + nombres
# ---------------------------------------------------------------------


def parametrize_by_kinds(
    template: Dict[str, Any],
    workflow_name_base: Optional[str],
    workflow_externalid_bases: Optional[List[str]],
    keyvault_name_base: Optional[str],
) -> Dict[str, Any]:
    """
    Aplica TODA la lógica, usando:
      - los mismos candidatos que la GUI (por literal)
      - y además los nombres de parámetros del bloque root.parameters.

      --workflow-name X
        → todos los workflows_*_name pasan a llamarse X

      --workflow-externalid Y --workflow-externalid Z ...
        → los parámetros workflows_*externalid se renombrarán en orden:
             1º → Y(_externalid)
             2º → Z(_externalid)
             ...

      --keyvault-name K
        → cualquier parámetro keyvault*name* pasa a llamarse K
    """
    import copy

    # Candidatos como en la GUI
    candidates = extract_literal_candidates_from_params_and_variables(template)

    literal_to_param: Dict[str, str] = {}
    param_renames: Dict[str, str] = {}   # old_param_name -> new_param_name
    externalid_params: Set[str] = set()
    selected_param_names: Set[str] = set()

    playbook_param_name: Optional[str] = None
    keyvault_param_name: Optional[str] = None

    # Cola para los externalid (aplicados en orden)
    extid_queue: List[str] = []
    if workflow_externalid_bases:
        for base in workflow_externalid_bases:
            if base:
                extid_queue.append(ensure_externalid_suffix(base))

    # ------------------------------------------------------------------
    # 1) Usar candidatos (igual que la GUI) para mapear literal -> parámetro
    # ------------------------------------------------------------------
    for literal, info in candidates.items():
        used_in = info.get("used_in", []) or []

        # Extraer nombres de parámetros ARM donde aparece ese literal
        original_param_names: List[str] = []
        prefix = "ARM parameter '"
        for u in used_in:
            if isinstance(u, str) and u.startswith(prefix) and u.endswith("'"):
                original_param_names.append(u[len(prefix):-1])

        if not original_param_names:
            continue

        for old_param_name in original_param_names:
            new_name: Optional[str] = None
            lname = old_param_name.lower()

            # 1) workflows_*_name
            if (
                workflow_name_base
                and old_param_name.startswith("workflows_")
                and old_param_name.endswith("_name")
            ):
                new_name = workflow_name_base
                playbook_param_name = new_name

            # 2) workflows_*externalid (con la cola en orden)
            elif (
                extid_queue
                and old_param_name.startswith("workflows_")
                and "externalid" in lname
            ):
                new_name = extid_queue.pop(0)
                externalid_params.add(new_name)

            # 3) keyvault_*name*
            elif (
                keyvault_name_base
                and "keyvault" in lname
                and "name" in lname
            ):
                new_name = keyvault_name_base
                keyvault_param_name = new_name

            if new_name is None:
                continue

            # Literal -> nuevo param (igual que en la GUI)
            literal_to_param[literal] = new_name
            selected_param_names.add(new_name)

            # Registrar renombre de parámetro si cambia
            if old_param_name != new_name:
                param_renames[old_param_name] = new_name

    # ------------------------------------------------------------------
    # 2) EXTRA: escanear TODOS los parámetros del bloque root.parameters
    #    para detectar workflows_* y keyvault_* aunque no tengan literal.
    # ------------------------------------------------------------------
    params_block = template.get("parameters", {})
    if isinstance(params_block, dict):
        for old_name in params_block.keys():
            if old_name in param_renames:
                continue  # ya procesado por candidatos

            new_name: Optional[str] = None
            lname = old_name.lower()

            # workflows_*_name
            if (
                workflow_name_base
                and old_name.startswith("workflows_")
                and old_name.endswith("_name")
            ):
                new_name = workflow_name_base
                playbook_param_name = new_name

            # workflows_*externalid
            elif (
                extid_queue
                and old_name.startswith("workflows_")
                and "externalid" in lname
            ):
                new_name = extid_queue.pop(0)
                externalid_params.add(new_name)

            # keyvault_*name*
            elif (
                keyvault_name_base
                and "keyvault" in lname
                and "name" in lname
            ):
                new_name = keyvault_name_base
                keyvault_param_name = new_name

            if new_name is None:
                continue

            param_renames[old_name] = new_name
            selected_param_names.add(new_name)

    if not param_renames and not literal_to_param:
        print(
            "[ERROR] No se ha encontrado ningún parámetro que coincida con los patrones indicados.",
            file=sys.stderr,
        )
        sys.exit(1)

    new_template = copy.deepcopy(template)

    # ------------------------------------------------------------------
    # 3) Renombrar parámetros en el bloque root.parameters
    # ------------------------------------------------------------------
    params_block_new = new_template.get("parameters", {})
    if not isinstance(params_block_new, dict):
        params_block_new = {}
        new_template["parameters"] = params_block_new

    updated_params: Dict[str, Any] = {}
    for old_name, pdef in params_block_new.items():
        if old_name in param_renames:
            new_name = param_renames[old_name]
            updated_params[new_name] = pdef
        else:
            updated_params[old_name] = pdef

    # Crear definiciones vacías para parámetros seleccionados que no existían antes
    for pname in selected_param_names:
        if pname not in updated_params:
            updated_params[pname] = {
                "type": "String"
            }

    new_template["parameters"] = updated_params

    # ------------------------------------------------------------------
    # 4) Actualizar referencias en el cuerpo (parameters('old') → parameters('new'))
    # ------------------------------------------------------------------
    body_without_params = {
        k: v for k, v in new_template.items() if k != "parameters"
    }

    rename_mapping = {}
    for old_name, new_name in param_renames.items():
        rename_mapping[f"parameters('{old_name}')"] = f"parameters('{new_name}')"
        rename_mapping[f"[parameters('{old_name}')"] = f"[parameters('{new_name}')"

    if rename_mapping:
        body_without_params = replace_substrings(body_without_params, rename_mapping)

    # ------------------------------------------------------------------
    # 5) Reemplazar literales por parámetros (solo para los que tienen literal)
    # ------------------------------------------------------------------
    if literal_to_param:
        body_without_params = replace_literals(body_without_params, literal_to_param)

    # Reconstruir template completo
    final_template: Dict[str, Any] = {}
    final_template["parameters"] = new_template.get("parameters", {})
    for k, v in body_without_params.items():
        final_template[k] = v

    # ------------------------------------------------------------------
    # 6) Añadir definiciones de parámetros (en caso de que falten)
    # ------------------------------------------------------------------
    if literal_to_param:
        add_parameter_definitions(final_template, literal_to_param)

    # ------------------------------------------------------------------
    # 7) Quedarse SOLO con los parámetros seleccionados
    # ------------------------------------------------------------------
    keep_only_selected_parameters(final_template, selected_param_names)

    # ------------------------------------------------------------------
    # 8) Ajustar defaults, externalid, variables, conexiones, etc.
    # ------------------------------------------------------------------

    # 8.1. defaultValue = nombre del parámetro
    overwrite_parameter_defaults_with_names(final_template)

    # 8.2. Default especial para *_externalid (concat(...) al workflow del playbook)
    set_externalid_defaults(final_template, externalid_params, playbook_param_name)

    # 8.3. variables (AzureSentinel + keyvault condicional)
    ensure_default_variables(final_template, playbook_param_name)

    # 8.4. $connections en workflows
    ensure_connections_blocks(final_template)

    # 8.5. Recursos Microsoft.Web/connections
    ensure_connection_resources(final_template, keyvault_param_name)

    # 8.6. definition.parameters con referencias a parameters('X')
    ensure_definition_parameters(final_template)

    return final_template


# ---------------------------------------------------------------------
# CLI main
# ---------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Parametriza un ARM template de Sentinel/Logic Apps renombrando "
            "parámetros por TIPO (workflows_*_name, workflows_*externalid, "
            "keyvault_*name*, etc.), usando los mismos candidatos que la GUI "
            "y además los nombres del bloque parameters."
        )
    )
    parser.add_argument(
        "-f", "--file", "--input",
        dest="input",
        required=True,
        help="Archivo JSON de entrada (raw template)"
    )
    parser.add_argument(
        "-o", "--output",
        dest="output",
        required=True,
        help="Archivo JSON de salida (parametrizado)"
    )
    parser.add_argument(
        "--workflow-name",
        help="Nombre base para TODOS los parámetros workflows_*_name"
    )
    parser.add_argument(
        "--workflow-externalid",
        action="append",
        dest="workflow_externalid_bases",
        help=(
            "Nombre base para los parámetros workflows_*externalid. "
            "Se aplica en orden de aparición. "
            "Se puede repetir varias veces. "
            "Se añadirá sufijo _externalid si no lo tiene."
        )
    )
    parser.add_argument(
        "--keyvault-name",
        help="Nombre para el parámetro de tipo keyvault_*name* (normalmente el vaultName)."
    )

    args = parser.parse_args()

    if not (args.workflow_name or args.workflow_externalid_bases or args.keyvault_name):
        print(
            "[ERROR] Debes indicar al menos una de las opciones: "
            "--workflow-name, --workflow-externalid, --keyvault-name.",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as f:
        template = json.load(f)

    new_template = parametrize_by_kinds(
        template=template,
        workflow_name_base=args.workflow_name,
        workflow_externalid_bases=args.workflow_externalid_bases,
        keyvault_name_base=args.keyvault_name,
    )

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(new_template, f, indent=4, ensure_ascii=False)
        f.write("\n")


if __name__ == "__main__":
    main()
