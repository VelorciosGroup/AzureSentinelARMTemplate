import argparse
import json
import sys
from typing import Dict, Any, Set, Optional

from .core import replace_literals, replace_substrings, add_parameter_definitions


# ---------------------------------------------------------------------
# Parseo de argumentos --param
# ---------------------------------------------------------------------


def parse_param_args(param_args) -> Dict[str, str]:
    """
    Convierte:
        -p NombreParam=Literal
        -p OtroParam=OtroLiteral

    En:
        {
          "Literal": "NombreParam",
          "OtroLiteral": "OtroParam"
        }
    """
    params: Dict[str, str] = {}
    for arg in param_args or []:
        if "=" not in arg:
            print(f"[WARN] Ignoring --param '{arg}' (no name=value)", file=sys.stderr)
            continue
        name, value = arg.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name:
            print(f"[WARN] Ignoring --param '{arg}' (empty name)", file=sys.stderr)
            continue
        # IMPORTANTE: literal -> nombre_param
        params[value] = name
    return params


# ---------------------------------------------------------------------
# Funciones compartidas con la GUI (adaptadas)
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
    literal_to_param: Dict[str, str]
) -> None:
    """Deja en template['parameters'] solo los nombres de literal_to_param."""
    params = template.get("parameters", {})
    if not isinstance(params, dict):
        return

    allowed_names = set(literal_to_param.values())
    new_params = {
        pname: pdef
        for pname, pdef in params.items()
        if pname in allowed_names
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
    """Garantiza que el nombre termine en _externalid (case-insensitive)."""
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
# Parametrización usando SOLO los literales que pasan por CLI
# ---------------------------------------------------------------------


def parametrize_with_cli(
    template: Dict[str, Any],
    cli_literal_to_param: Dict[str, str]
) -> Dict[str, Any]:
    """
    Aplica TODA la lógica, pero SOLO a los literales que el usuario pasa
    por CLI con --param.
    """
    import copy

    candidates = extract_literal_candidates_from_params_and_variables(template)

    literal_to_param_final: Dict[str, str] = {}
    workflow_renames: Dict[str, str] = {}
    playbook_param_name: Optional[str] = None
    keyvault_param_name: Optional[str] = None
    externalid_params: Set[str] = set()

    # Para cada literal que el usuario ha pasado en CLI
    for literal, param_name_from_cli in cli_literal_to_param.items():
        new_param_name = param_name_from_cli

        meta = candidates.get(literal, {})
        used_in = meta.get("used_in", []) or []

        original_param_names = []
        prefix = "ARM parameter '"
        for u in used_in:
            if isinstance(u, str) and u.startswith(prefix) and u.endswith("'"):
                original_param_names.append(u[len(prefix):-1])

        # Sufijo externalid
        for old_param_name in original_param_names:
            if old_param_name.lower().endswith("externalid"):
                new_param_name = ensure_externalid_suffix(new_param_name)
                externalid_params.add(new_param_name)
                break

        # Guardar mapping literal → nombre final
        literal_to_param_final[literal] = new_param_name

        # Detectar playbook_param_name, keyvault_param_name y renames
        for old_param_name in original_param_names:
            if old_param_name.startswith("workflows_") and old_param_name.endswith("_name"):
                playbook_param_name = new_param_name

            if "keyvault" in old_param_name.lower() and "name" in old_param_name.lower():
                keyvault_param_name = new_param_name

            if old_param_name.startswith("workflows_") and old_param_name != new_param_name:
                workflow_renames[old_param_name] = new_param_name

    if not literal_to_param_final:
        print("[ERROR] No valid literals matched for the provided --param values.", file=sys.stderr)
        sys.exit(1)

    new_template = copy.deepcopy(template)

    # 1. Renombrar parámetros workflows existentes
    params_block = new_template.get("parameters", {})
    if isinstance(params_block, dict):
        for old_name, new_name in workflow_renames.items():
            if old_name in params_block:
                definition = params_block.pop(old_name)
                params_block[new_name] = definition
        new_template["parameters"] = params_block

    # 2. Body sin parameters
    body_without_params = {
        k: v for k, v in new_template.items() if k != "parameters"
    }

    # 3. Actualizar referencias de parámetros (workflows_... -> nuevo)
    rename_mapping = {}
    for old_name, new_name in workflow_renames.items():
        rename_mapping[f"parameters('{old_name}')"] = f"parameters('{new_name}')"
        rename_mapping[f"[parameters('{old_name}')"] = f"[parameters('{new_name}')"

    if rename_mapping:
        body_without_params = replace_substrings(body_without_params, rename_mapping)

    # 4. Reemplazar literales (solo los que pasan por CLI; no toca expresiones ARM)
    body_without_params = replace_literals(body_without_params, literal_to_param_final)

    # Reconstruir template
    final_template: Dict[str, Any] = {}
    final_template["parameters"] = new_template.get("parameters", {})
    for k, v in body_without_params.items():
        final_template[k] = v

    # 5. Añadir definiciones de parámetros base
    add_parameter_definitions(final_template, literal_to_param_final)

    # 6. Quedarse solo con los parámetros seleccionados (CLI)
    keep_only_selected_parameters(final_template, literal_to_param_final)

    # 7. defaultValue = nombre del parámetro
    overwrite_parameter_defaults_with_names(final_template)

    # 7.1. defaultValue especial para *_externalid
    set_externalid_defaults(final_template, externalid_params, playbook_param_name)

    # 8. variables (AzureSentinel + keyvault condicional)
    ensure_default_variables(final_template, playbook_param_name)

    # 9. $connections en workflows
    ensure_connections_blocks(final_template)

    # 10. Recursos Microsoft.Web/connections
    ensure_connection_resources(final_template, keyvault_param_name)

    # 11. definition.parameters con referencias a parameters('X')
    ensure_definition_parameters(final_template)

    return final_template


# ---------------------------------------------------------------------
# CLI main
# ---------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Parametrize ARM template by replacing specific literals with parameters (Sentinel/Logic Apps aware)."
    )
    parser.add_argument("-i", "--input", required=True, help="Input ARM template JSON")
    parser.add_argument("-o", "--output", required=True, help="Output ARM template JSON")
    parser.add_argument(
        "-p",
        "--param",
        action="append",
        help="Parameter definition in the form paramName=literalValue. Can be repeated."
    )
    args = parser.parse_args()

    literal_to_param_cli = parse_param_args(args.param)
    if not literal_to_param_cli:
        print("[ERROR] No parameters provided (--param).", file=sys.stderr)
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as f:
        template = json.load(f)

    new_template = parametrize_with_cli(template, literal_to_param_cli)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(new_template, f, indent=4, ensure_ascii=False)
        f.write("\n")


if __name__ == "__main__":
    main()
