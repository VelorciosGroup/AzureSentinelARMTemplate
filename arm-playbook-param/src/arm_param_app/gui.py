import json
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Dict, Any

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
        info["suggested_param"] = pname[:80]  # ← aumentado de 40 a 80

    return candidates


class ParamGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("ARM Playbook Parametrizer")

        self.template = None
        self.checkbox_vars: Dict[str, tk.IntVar] = {}
        self.entry_vars: Dict[str, tk.StringVar] = {}
        self.candidates_meta: Dict[str, Dict[str, Any]] = {}

        self.file_label = tk.Label(root, text="No file loaded")
        self.file_label.pack(pady=5)

        self.load_button = tk.Button(
            root,
            text="Load ARM template JSON",
            command=self.load_file
        )
        self.load_button.pack(pady=5)

        # Frame con scroll vertical
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

        for literal, info in self.candidates_meta.items():
            used_in = info.get("used_in", [])
            suggested = info.get("suggested_param", "")
            count = len(used_in)

            frame = tk.Frame(self.scroll_frame, bd=1, relief=tk.GROOVE, padx=4, pady=2)
            frame.pack(fill="x", padx=2, pady=2)

            var = tk.IntVar(value=0)
            self.checkbox_vars[literal] = var
            tk.Checkbutton(frame, variable=var).grid(row=0, column=0, rowspan=3, sticky="nw")

            pvar = tk.StringVar(value=suggested)
            self.entry_vars[literal] = pvar

            tk.Label(frame, text=f"Literal (used in {count} place(s)):").grid(row=0, column=1, sticky="w")

            # ←← literal COMPLETO, sin truncar y sin wrap
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
                    wraplength=0,         # ← sin wrap
                    justify="left",
                    fg="gray20"
                ).grid(row=1, column=1, columnspan=2, sticky="w")

            tk.Label(frame, text="Param name:").grid(row=2, column=1, sticky="e")
            tk.Entry(frame, textvariable=pvar, width=80).grid(row=2, column=2, sticky="w")   # ← ancho 80

    def parametrize_selected(self) -> None:
        if self.template is None:
            messagebox.showerror("Error", "No template loaded.")
            return

        import copy
        literal_to_param: Dict[str, str] = {}
        workflow_renames: Dict[str, str] = {}

        for literal, var in self.checkbox_vars.items():
            if not var.get():
                continue

            new_param_name = self.entry_vars[literal].get().strip()
            if not new_param_name:
                messagebox.showerror("Error", f"Parameter name for literal '{literal[:50]}' is empty.")
                return

            literal_to_param[literal] = new_param_name

            meta = self.candidates_meta.get(literal, {})
            used_in = meta.get("used_in", [])

            prefix = "ARM parameter '"
            for u in used_in:
                if u.startswith(prefix) and u.endswith("'"):
                    old_param_name = u[len(prefix):-1]
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

        # 3. Actualizar referencias
        from .core import replace_substrings

        rename_mapping = {}
        for old_name, new_name in workflow_renames.items():
            rename_mapping[f"parameters('{old_name}')"] = f"parameters('{new_name}')"
            rename_mapping[f"[parameters('{old_name}')"] = f"[parameters('{new_name}')"

        if rename_mapping:
            body_without_params = replace_substrings(body_without_params, rename_mapping)

        # 4. Reemplazar literales
        body_without_params = replace_literals(body_without_params, literal_to_param)

        final_template: Dict[str, Any] = {}
        final_template["parameters"] = new_template.get("parameters", {})
        for k, v in body_without_params.items():
            final_template[k] = v

        add_parameter_definitions(final_template, literal_to_param)

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
