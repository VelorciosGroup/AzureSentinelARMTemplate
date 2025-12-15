import json
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Dict, Any, Set, Optional

from .core import replace_literals, add_parameter_definitions


def extract_literal_candidates_from_params_and_variables(
    template: Dict[str, Any]
) -> Dict[str, Dict[str, Any]]:
    """
    Escanea el template ARM y devuelve un diccionario:

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

    # 3) Post-proceso: limpiar nombres sugeridos
    for lit, info in candidates.items():
        pname = info.get("suggested_param") or ""
        pname = pname.strip().replace(" ", "_").replace("-", "_").replace("/", "_")
        if not pname:
            pname = "param"
        if not pname[0].isalpha():
            pname = "p_" + pname
        info["suggested_param"] = pname[:80]

    return candidates


# ----------------- Detección uso de Key Vault ----------------- #

def uses_keyvault_connection(template: Dict[str, Any]) -> bool:
    """
    Devuelve True si el template usa algo relacionado con Key Vault.
    Heurística simple: buscamos 'keyvault' en el JSON entero.
    Ajusta esta lógica si necesitas algo más fino.
    """
    try:
        dumped = json.dumps(template).lower()
    except TypeError:
        return False
    return "keyvault" in dumped


# ----------------- Variables por defecto ----------------- #

def ensure_default_variables(
    template: Dict[str, Any],
    playbook_param_name: Optional[str] = None
) -> None:
    """
    Asegura que en template['variables'] existan:
      - AzureSentinelConnectionName
      - keyvault_Connection_Name (solo si se detecta uso de Key Vault)

    Usa el parámetro que represente el nombre del playbook:
    [concat('azuresentinel-', parameters('<playbook_param_name>'))]

    Si no se detecta, cae por defecto a 'PlaybookName'.
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


# ----------------- Bloque $connections en el workflow ----------------- #

def ensure_connections_blocks(template: Dict[str, Any]) -> None:
    """
    Asegura que en cada workflow (Microsoft.Logic/workflows) exista el bloque:

      properties.parameters.$connections.value.azuresentinel / keyvault

    y ajusta/crea también el dependsOn del workflow para:
      - Microsoft.Web/connections AzureSentinelConnectionName (siempre)
      - Microsoft.Web/connections keyvault_Connection_Name (solo si se usa Key Vault)
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

        # Bloque azuresentinel (siempre)
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

        # Bloque keyvault condicional
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

        # Crear/ajustar dependsOn siempre
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
            # limpiamos posibles duplicados de estas dos entradas
            if d in (az_dep, kv_dep):
                continue
            new_depends.append(d)

        # Siempre Azure Sentinel
        if az_dep not in new_depends:
            new_depends.append(az_dep)

        # Key Vault solo si se usa
        if keyvault_used and kv_dep not in new_depends:
            new_depends.append(kv_dep)

        res["dependsOn"] = new_depends


# ----------------- Recursos Microsoft.Web/connections ----------------- #

def ensure_connection_resources(
    template: Dict[str, Any],
    keyvault_param_name: Optional[str] = None
) -> None:
    """
    Asegura que existan los recursos de tipo 'Microsoft.Web/connections'
    para:
      - AzureSentinelConnectionName (siempre)
      - keyvault_Connection_Name (solo si se usa Key Vault)

    En el de Key Vault, 'vaultName' usará el parámetro real pasado en
    keyvault_param_name (si existe), o 'keyvault_Name' por defecto.
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

    # Recurso Azure Sentinel (siempre)
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

    # Recurso Key Vault (solo si se usa)
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


# ----------------- Sobrescribir defaultValue de parámetros ----------------- #

def overwrite_parameter_defaults_with_names(template: Dict[str, Any]) -> None:
    """
    Hace que todos los parámetros de tipo String tengan:
      defaultValue = "<nombre_del_parametro>"
    """
    params = template.get("parameters", {})
    if not isinstance(params, dict):
        return

    for pname, pdef in params.items():
        if not isinstance(pdef, dict):
            continue
        ptype = pdef.get("type")
        if isinstance(ptype, str) and ptype.lower() == "string":
            pdef["defaultValue"] = pname


# ----------------- Dejar solo parámetros seleccionados ----------------- #

def keep_only_selected_parameters(
    template: Dict[str, Any],
    literal_to_param: Dict[str, str]
) -> None:
    """
    Deja en template['parameters'] SOLO los parámetros cuyos nombres
    son los que el usuario ha definido en la GUI (literal_to_param.values()).
    """
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


# ------------- parameters dentro de properties.definition --------------- #

def ensure_definition_parameters(template: Dict[str, Any]) -> None:
    """
    Para cada workflow Microsoft.Logic/workflows mete en
    properties.definition.parameters todos los parámetros definidos en
    template['parameters'].

    Se referencian así:
      "MiParametro": {
        "type": "String",
        "defaultValue": "[parameters('MiParametro')]"
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


# ------------- Lógica especial para parámetros *_externalid ------------- #

def ensure_externalid_suffix(name: str) -> str:
    """Garantiza que el nombre termine en _externalid (case-insensitive)."""
    low = name.lower()
    if low.endswith("_externalid"):
        return name
    if low.endswith("externalid"):
        # ya lleva externalid sin guion bajo
        return name
    return f"{name}_externalid"


def set_externalid_defaults(
    template: Dict[str, Any],
    externalid_param_names: Set[str],
    playbook_param_name: Optional[str]
) -> None:
    """
    Pone en cada parámetro <extid> el defaultValue con el concat(...) que
    referencia al parámetro de nombre del playbook:

    [concat('/subscriptions/', subscription().subscriptionId,
            '/resourceGroups/', resourceGroup().name,
            '/providers/Microsoft.Logic/workflows/',
            parameters('<playbook_param_name>'))]
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


# ------------------------------------------------------------------- #


class ParamGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("ARM Playbook Parametrizer")

        self.template = None
        self.checkbox_vars: Dict[str, tk.IntVar] = {}
        self.entry_vars: Dict[str, tk.StringVar] = {}
        self.candidates_meta: Dict[str, Dict[str, Any]] = {}

        self.toggle_all_btn: Optional[tk.Button] = None

        self.file_label = tk.Label(root, text="No file loaded")
        self.file_label.pack(pady=5)

        self.load_button = tk.Button(
            root,
            text="Load ARM template JSON",
            command=self.load_file
        )
        self.load_button.pack(pady=5)

        self.candidates_frame = tk.Frame(root)
        self.candidates_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.candidates_frame)
        self.scrollbar = tk.Scrollbar(
            self.candidates_frame, orient="vertical", command=self.canvas.yview
        )
        self.scroll_frame = tk.Frame(self.canvas)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.param_button = tk.Button(
            root,
            text="Parametrize selected",
            command=self.parametrize_selected
        )
        self.param_button.pack(pady=5)

    def load_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Select ARM template JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.template = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load JSON: {e}")
            return

        self.file_label.config(text=f"Loaded: {path}")
        self.build_candidates()

    def build_candidates(self) -> None:
        for w in self.scroll_frame.winfo_children():
            w.destroy()
        self.checkbox_vars.clear()
        self.entry_vars.clear()
        self.candidates_meta.clear()
        self.toggle_all_btn = None

        if not isinstance(self.template, dict):
            messagebox.showerror("Error", "Root JSON must be an object.")
            return

        self.candidates_meta = extract_literal_candidates_from_params_and_variables(
            self.template
        )

        if not self.candidates_meta:
            tk.Label(
                self.scroll_frame,
                text="No parameters/variables with string values found."
            ).pack()
            return

        tk.Label(
            self.scroll_frame,
            text="Select literals (from parameters/variables) to parametrize and optionally edit parameter name:"
        ).pack(anchor="w", pady=2)

        # Botón toggle seleccionar/deseleccionar todas
        self.toggle_all_btn = tk.Button(
            self.scroll_frame,
            text="Deseleccionar todas",
            command=self.toggle_all_literals
        )
        self.toggle_all_btn.pack(anchor="w", pady=(0, 5))

        for literal, info in self.candidates_meta.items():
            used_in = info.get("used_in", [])
            suggested = info.get("suggested_param", "")
            count = len(used_in)

            frame = tk.Frame(self.scroll_frame, bd=1, relief=tk.GROOVE, padx=4, pady=2)
            frame.pack(fill="x", padx=2, pady=2)

            var = tk.IntVar(value=1)
            self.checkbox_vars[literal] = var
            tk.Checkbutton(frame, variable=var).grid(row=0, column=0, rowspan=3, sticky="nw")

            pvar = tk.StringVar(value=suggested)
            self.entry_vars[literal] = pvar

            tk.Label(frame, text=f"Literal (used in {count} place(s)):").grid(row=0, column=1, sticky="w")

            tk.Label(
                frame,
                text=literal,
                wraplength=0,
                justify="left"
            ).grid(row=0, column=2, sticky="w")

            if used_in:
                where_text = "; ".join(used_in)
                tk.Label(
                    frame,
                    text=f"Used in: {where_text}",
                    wraplength=0,
                    justify="left",
                    fg="gray20"
                ).grid(row=1, column=1, columnspan=2, sticky="w")

            tk.Label(frame, text="Param name:").grid(row=2, column=1, sticky="e")
            tk.Entry(frame, textvariable=pvar, width=80).grid(row=2, column=2, sticky="w")

    def toggle_all_literals(self) -> None:
        vars_list = list(self.checkbox_vars.values())
        if not vars_list:
            return

        all_checked = all(v.get() == 1 for v in vars_list)

        if all_checked:
            for v in vars_list:
                v.set(0)
            if self.toggle_all_btn is not None:
                self.toggle_all_btn.config(text="Seleccionar todas")
        else:
            for v in vars_list:
                v.set(1)
            if self.toggle_all_btn is not None:
                self.toggle_all_btn.config(text="Deseleccionar todas")

    def parametrize_selected(self) -> None:
        if self.template is None:
            messagebox.showerror("Error", "No template loaded.")
            return

        import copy
        literal_to_param: Dict[str, str] = {}
        workflow_renames: Dict[str, str] = {}
        playbook_param_name: Optional[str] = None
        keyvault_param_name: Optional[str] = None
        externalid_params: Set[str] = set()

        for literal, var in self.checkbox_vars.items():
            if not var.get():
                continue

            new_param_name = self.entry_vars[literal].get().strip()
            if not new_param_name:
                messagebox.showerror(
                    "Error",
                    f"Parameter name for literal '{literal[:50]}' is empty."
                )
                return

            meta = self.candidates_meta.get(literal, {})
            used_in = meta.get("used_in", [])

            # Encontrar nombres originales de parámetros ARM
            original_param_names = []
            prefix = "ARM parameter '"
            for u in used_in:
                if u.startswith(prefix) and u.endswith("'"):
                    original_param_names.append(u[len(prefix):-1])

            # Si alguno de los nombres originales termina en externalid,
            # forzamos sufijo en el nuevo nombre y lo marcamos.
            for old_param_name in original_param_names:
                if old_param_name.lower().endswith("externalid"):
                    new_param_name = ensure_externalid_suffix(new_param_name)
                    externalid_params.add(new_param_name)
                    break

            # Guardamos el mapping literal → nombre de parámetro final
            literal_to_param[literal] = new_param_name

            # Detectar playbook_param_name, keyvault_param_name y renames
            for old_param_name in original_param_names:
                # detectar parámetro de nombre de playbook
                if old_param_name.startswith("workflows_") and old_param_name.endswith("_name"):
                    playbook_param_name = new_param_name

                # detectar parámetro de nombre de Key Vault (ej. keyvault_Name)
                if "keyvault" in old_param_name.lower() and "name" in old_param_name.lower():
                    keyvault_param_name = new_param_name

                if old_param_name.startswith("workflows_") and old_param_name != new_param_name:
                    workflow_renames[old_param_name] = new_param_name

        if not literal_to_param:
            messagebox.showinfo("Info", "No literals selected.")
            return

        new_template = copy.deepcopy(self.template)

        # 1. Renombrar parámetros workflows existentes
        params_block = new_template.get("parameters", {})
        if isinstance(params_block, dict):
            for old_name, new_name in workflow_renames.items():
                if old_name in params_block:
                    definition = params_block.pop(old_name)
                    params_block[new_name] = definition
            new_template["parameters"] = params_block

        # 2. Separar bloque parameters
        body_without_params = {
            k: v for k, v in new_template.items() if k != "parameters"
        }

        # 3. Actualizar referencias de parámetros (workflows_... -> nuevo nombre)
        from .core import replace_substrings

        rename_mapping = {}
        for old_name, new_name in workflow_renames.items():
            rename_mapping[f"parameters('{old_name}')"] = f"parameters('{new_name}')"
            rename_mapping[f"[parameters('{old_name}')"] = f"[parameters('{new_name}')"

        if rename_mapping:
            body_without_params = replace_substrings(body_without_params, rename_mapping)

        # 4. Reemplazar literales (no toca expresiones ARM si has ajustado replace_literals en core.py)
        body_without_params = replace_literals(body_without_params, literal_to_param)

        final_template: Dict[str, Any] = {}
        final_template["parameters"] = new_template.get("parameters", {})
        for k, v in body_without_params.items():
            final_template[k] = v

        # 5. Añadir definiciones de parámetros (core)
        add_parameter_definitions(final_template, literal_to_param)

        # 6. Quedarse solo con los parámetros seleccionados
        keep_only_selected_parameters(final_template, literal_to_param)

        # 7. defaultValue = nombre del parámetro
        overwrite_parameter_defaults_with_names(final_template)

        # 7.1. Ajustar defaultValue de *_externalid al concat(...)
        set_externalid_defaults(final_template, externalid_params, playbook_param_name)

        # 8. Variables por defecto (AzureSentinel + keyvault condicional)
        ensure_default_variables(final_template, playbook_param_name)

        # 9. Bloque $connections en workflows
        ensure_connections_blocks(final_template)

        # 10. Recursos Microsoft.Web/connections
        ensure_connection_resources(final_template, keyvault_param_name)

        # 11. Meter todos los parámetros en properties.definition.parameters
        ensure_definition_parameters(final_template)

        out_path = filedialog.asksaveasfilename(
            title="Save parametrized template",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not out_path:
            return

        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(final_template, f, indent=4, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save JSON: {e}")
            return

        messagebox.showinfo("Success", f"Parametrized template saved to:\n{out_path}")


def main():
    root = tk.Tk()
    app = ParamGUI(root)
    root.geometry("1000x700")
    root.mainloop()


if __name__ == "__main__":
    main()
