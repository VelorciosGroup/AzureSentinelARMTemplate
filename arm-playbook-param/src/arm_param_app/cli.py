import argparse
import json
import sys
from typing import Dict, Any, Set, Optional, List

from .core import replace_literals, replace_substrings, add_parameter_definitions


# ---------------------------------------------------------------------
# Extracción de candidatos (igual que la GUI)
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

    Y que AlternativeParameterValues.vaultName apunte al parámetro de Key Vault correcto.
    """
    resources = template.setdefault("resources", [])
    if not isinstance(resources, list):
        return

    keyvault_used = uses_keyvault_connection(template)

    # Inferir nombre del parámetro de Key Vault si no viene dado
    if not keyvault_param_name:
        params = template.get("parameters", {})
        if isinstance(params, dict):
            for pname in params.keys():
                lname = pname.lower()
                if "keyvault" in lname and "name" in lname:
                    keyvault_param_name = pname
                    break

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
            # Actualizar también vaultName aquí por si ya existía
            props = res.setdefault("properties", {})
            alt = props.setdefault("AlternativeParameterValues", {})
            alt["vaultName"] = f"[parameters('{keyvault_param_name}')]"

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
# Parametrización guiada por CLI (mismo modelo que GUI, pero automático)
# ---------------------------------------------------------------------


def parametrize_from_cli(
    template: Dict[str, Any],
    playbook_name_param: Optional[str],
    externalid_names: Optional[List[str]],
    keyvault_names: Optional[List[str]],
) -> Dict[str, Any]:
    """
    Hace lo mismo que la GUI, pero:

    - Identifica candidatos (literales) igual que la GUI.
    - En vez de preguntarte, asigna nombres según la CLI:

      --name X
        → workflows_*_name  → X

      --externalid A --externalid B ...
        → workflows_*externalid  → A, B, ...

      --keyvault KV_NAME KV_CLIENTID KV_SECRET KV_BASEURL
        → primer nombre para el vault (vaultName)
        → los demás se asignan en orden a ClientID, ClientSecret, BaseUrl
    """
    import copy

    candidates = extract_literal_candidates_from_params_and_variables(template)

    # Mapeos que vamos a construir
    literal_to_param: Dict[str, str] = {}
    workflow_renames: Dict[str, str] = {}  # old_param_name -> new_param_name
    selected_param_names: Set[str] = set()
    externalid_param_names: Set[str] = set()

    playbook_param_name: Optional[str] = None
    keyvault_param_name: Optional[str] = None  # nombre del parámetro de vault

    # ------------------------------------------------------------------
    # 1) Clasificar candidatos: workflow name, externalid, keyvault secrets
    # ------------------------------------------------------------------
    workflow_name_literals: List[tuple[str, str]] = []      # (literal, old_param_name)
    externalid_literals: List[tuple[str, str]] = []         # (literal, old_param_name)
    keyvault_secret_literals: List[tuple[str, str]] = []    # (literal, var_role)

    for literal, info in candidates.items():
        used_in = info.get("used_in", []) or []

        param_names: List[str] = []
        var_names: List[str] = []

        for u in used_in:
            if not isinstance(u, str):
                continue

            # ARM parameter 'X'
            if u.startswith("ARM parameter '") and u.endswith("'"):
                pname = u[len("ARM parameter '"):-1]
                param_names.append(pname)

            # Variable 'Y' (action 'Z')
            if u.startswith("Variable '"):
                # Variable 'ClientID' (action 'Initialize_variable_ClientID')
                try:
                    after = u[len("Variable '"):]
                    vname = after.split("'", 1)[0]
                    var_names.append(vname)
                except Exception:
                    pass

        # Detectar workflow name y externalid por nombres de parámetro
        for pname in param_names:
            lname = pname.lower()
            if pname.startswith("workflows_") and pname.endswith("_name"):
                workflow_name_literals.append((literal, pname))
            elif pname.startswith("workflows_") and "externalid" in lname:
                externalid_literals.append((literal, pname))

        # Detectar keyvault secrets por nombre de variable (ClientID, ClientSecret, BaseUrl)
        for vname in var_names:
            vn_low = vname.lower()
            if vn_low == "clientid":
                keyvault_secret_literals.append((literal, "ClientID"))
            elif vn_low == "clientsecret":
                keyvault_secret_literals.append((literal, "ClientSecret"))
            elif vn_low in ("baseurl", "base_url", "baseurl"):
                keyvault_secret_literals.append((literal, "BaseUrl"))

    # Orden estable para externalid (por nombre de parámetro)
    externalid_literals.sort(key=lambda x: x[1])
    # Orden para keyvault secrets según rol conocido
    role_order = {"ClientID": 0, "ClientSecret": 1, "BaseUrl": 2}
    keyvault_secret_literals.sort(key=lambda x: role_order.get(x[1], 99))

    # ------------------------------------------------------------------
    # 2) Asignar nombres según CLI
    # ------------------------------------------------------------------

    # 2.1. Playbook Name
    if playbook_name_param:
        for literal, old_pname in workflow_name_literals:
            literal_to_param[literal] = playbook_name_param
            workflow_renames[old_pname] = playbook_name_param
            selected_param_names.add(playbook_name_param)
            playbook_param_name = playbook_name_param

    # 2.2. External IDs
    if externalid_names:
        ext_queue = list(externalid_names)
        for (literal, old_pname), new_name in zip(externalid_literals, ext_queue):
            literal_to_param[literal] = new_name
            workflow_renames[old_pname] = new_name
            selected_param_names.add(new_name)
            externalid_param_names.add(new_name)

    # 2.3. KeyVault
    keyvault_secret_param_names: List[str] = []
    if keyvault_names and len(keyvault_names) >= 1:
        keyvault_param_name = keyvault_names[0]
        selected_param_names.add(keyvault_param_name)

        if len(keyvault_names) > 1:
            keyvault_secret_param_names = keyvault_names[1:]

        for (literal, _role), pname in zip(
            keyvault_secret_literals, keyvault_secret_param_names
        ):
            literal_to_param[literal] = pname
            selected_param_names.add(pname)

    # Si no hay nada que hacer, error
    if not literal_to_param and not workflow_renames and not keyvault_param_name:
        print(
            "[ERROR] No se ha encontrado ningún candidato que coincida con lo pedido "
            "en --name / --externalid / --keyvault.",
            file=sys.stderr,
        )
        sys.exit(1)

    # ------------------------------------------------------------------
    # 3) Aplicar la transformación (igual filosofía que la GUI)
    # ------------------------------------------------------------------
    new_template = copy.deepcopy(template)

    # 3.1. Renombrar parámetros root de workflows_* (name y externalid)
    params_block = new_template.get("parameters", {})
    if not isinstance(params_block, dict):
        params_block = {}
        new_template["parameters"] = params_block

    for old_name, new_name in list(workflow_renames.items()):
        if old_name in params_block:
            definition = params_block.pop(old_name)
            params_block[new_name] = definition
    new_template["parameters"] = params_block

    # 3.2. Actualizar referencias parameters('old') → parameters('new') en el cuerpo
    body_without_params = {k: v for k, v in new_template.items() if k != "parameters"}

    rename_mapping = {}
    for old_name, new_name in workflow_renames.items():
        rename_mapping[f"parameters('{old_name}')"] = f"parameters('{new_name}')"
        rename_mapping[f"[parameters('{old_name}')"] = f"[parameters('{new_name}')"

    if rename_mapping:
        body_without_params = replace_substrings(body_without_params, rename_mapping)

    # 3.3. Reemplazar literales por parámetros (como en GUI)
    if literal_to_param:
        body_without_params = replace_literals(body_without_params, literal_to_param)

    # 3.4. Reconstruir template y añadir definiciones de parámetros nuevos
    final_template: Dict[str, Any] = {}
    final_template["parameters"] = new_template.get("parameters", {})
    for k, v in body_without_params.items():
        final_template[k] = v

    if literal_to_param:
        add_parameter_definitions(final_template, literal_to_param)

    # 3.5. Asegurar que el parámetro de KeyVault (vaultName) exista aunque no venga de literal
    if keyvault_param_name:
        params = final_template.setdefault("parameters", {})
        if keyvault_param_name not in params:
            params[keyvault_param_name] = {"type": "String"}
        selected_param_names.add(keyvault_param_name)

    # 3.6. Nos quedamos solo con los parámetros que hemos seleccionado
    if selected_param_names:
        keep_only_selected_parameters(final_template, selected_param_names)

    # ------------------------------------------------------------------
    # 4) Ajustes extra (igual que habíamos ido pidiendo en la GUI)
    # ------------------------------------------------------------------
    # 4.1. defaultValue = nombre del parámetro
    overwrite_parameter_defaults_with_names(final_template)

    # 4.2. Default especial para externalid (concat() al workflow del playbook)
    if externalid_param_names:
        set_externalid_defaults(final_template, externalid_param_names, playbook_param_name)

    # 4.3. variables (AzureSentinel + keyvault condicional)
    ensure_default_variables(final_template, playbook_param_name)

    # 4.4. $connections en workflows + dependsOn
    ensure_connections_blocks(final_template)

    # 4.5. Recursos Microsoft.Web/connections (incluido vaultName → parámetro correcto)
    ensure_connection_resources(final_template, keyvault_param_name)

    # 4.6. definition.parameters con referencias a parameters('X')
    ensure_definition_parameters(final_template)

    return final_template


# ---------------------------------------------------------------------
# CLI main
# ---------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Parametriza un ARM template de Sentinel/Logic Apps igual que la GUI, "
            "pero escogiendo los nombres de parámetros por línea de comandos "
            "(playbook name, externalid, keyvault...)."
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

    # Nombre del parámetro del playbook (workflows_*_name)
    parser.add_argument(
        "--name",
        dest="playbook_name_param",
        help="Nombre base para TODOS los parámetros workflows_*_name (PlaybookName)."
    )

    # External IDs (para workflows_*externalid). Se puede repetir.
    parser.add_argument(
        "--externalid",
        action="append",
        dest="externalid_names",
        help=(
            "Nombre de parámetro para workflows_*externalid. "
            "Se aplica en orden de aparición; puede repetirse varias veces."
        )
    )

    # KeyVault: primer nombre → parámetro de vaultName; el resto → secrets (ClientID, Secret, BaseUrl)
    parser.add_argument(
        "--keyvault",
        nargs="+",
        dest="keyvault_names",
        help=(
            "Nombres relacionados con Key Vault. "
            "El primer nombre se usa para el parámetro del vault (vaultName); "
            "los siguientes se aplican en orden a ClientID, ClientSecret, BaseUrl. "
            "Ej: --keyvault keyvault_Name keyvault_ClientID keyvault_Secret keyvault_BaseUrl"
        )
    )

    args = parser.parse_args()

    # Normalizar keyvault_names (porque con action='append' es una lista de listas/strings)
    keyvault_names_flat: Optional[List[str]] = None
    if args.keyvault_names:
        # Puedes pasar varios --keyvault, aquí lo aplanamos
        flat: List[str] = []
        for item in args.keyvault_names:
            # Permitimos que el usuario ponga una sola cadena con espacios
            # o una lista de valores; argparse nos lo da como string.
            if isinstance(item, str):
                # Split por espacios / comas si quiere
                parts = [p for p in item.replace(",", " ").split() if p]
                flat.extend(parts)
            else:
                # Por si acaso, aunque en la práctica deberían ser strings
                flat.extend(list(item))
        if flat:
            keyvault_names_flat = flat

    if not (args.playbook_name_param or args.externalid_names or keyvault_names_flat):
        print(
            "[ERROR] Debes indicar al menos una de las opciones: "
            "--name, --externalid o --keyvault.",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as f:
        template = json.load(f)

    new_template = parametrize_from_cli(
        template=template,
        playbook_name_param=args.playbook_name_param,
        externalid_names=args.externalid_names,
        keyvault_names=keyvault_names_flat,
    )

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(new_template, f, indent=4, ensure_ascii=False)
        f.write("\n")


if __name__ == "__main__":
    main()
