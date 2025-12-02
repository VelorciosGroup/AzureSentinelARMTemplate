from typing import Any, Dict


def replace_literals(obj: Any, literal_to_param: Dict[str, str]) -> Any:
    """
    Recorre el JSON (dict/list/str/...) y sustituye valores de tipo string que
    coincidan EXACTAMENTE con alguna clave de literal_to_param por la expresión:

        "[parameters('<nombre_param>')]"

    PERO:
    - Si la cadena parece una expresión ARM (empieza por "[" y termina en "]"),
      NO la tocamos. Así evitamos casos como:

        "[concat(..., parameters('Auth_Playbook_Name'))]"

      que antes se convertían erróneamente en:

        "[parameters('Auth_Playbook_Name')]"

    El cambio de nombres dentro de expresiones ARM lo hace replace_substrings.
    """
    # Diccionario
    if isinstance(obj, dict):
        return {k: replace_literals(v, literal_to_param) for k, v in obj.items()}

    # Lista
    if isinstance(obj, list):
        return [replace_literals(v, literal_to_param) for v in obj]

    # Cadena
    if isinstance(obj, str):
        # Si no es un literal que queramos parametrizar, lo dejamos tal cual
        if obj not in literal_to_param:
            return obj

        # Si parece una expresión ARM, no la tocamos aquí
        # (ejemplo: "[concat(...)]", "[parameters('X')]", etc.)
        if obj.startswith("[") and obj.endswith("]"):
            return obj

        param_name = literal_to_param[obj]
        return f"[parameters('{param_name}')]"

    # Cualquier otro tipo (int, bool, None, ...)
    return obj


def replace_substrings(obj: Any, mapping: Dict[str, str]) -> Any:
    """
    Recorre el JSON y, para cada string, aplica reemplazos de subcadenas
    según el diccionario mapping: { "viejo": "nuevo", ... }.

    Esto es lo que se usa, por ejemplo, para:
      parameters('workflows_X_name') -> parameters('PlaybookName')
    dentro de expresiones ARM como:

      "[concat(..., parameters('workflows_X_name'))]"
    """
    # Diccionario
    if isinstance(obj, dict):
        return {k: replace_substrings(v, mapping) for k, v in obj.items()}

    # Lista
    if isinstance(obj, list):
        return [replace_substrings(v, mapping) for v in obj]

    # Cadena
    if isinstance(obj, str):
        new_s = obj
        for old, new in mapping.items():
            if old in new_s:
                new_s = new_s.replace(old, new)
        return new_s

    # Otros tipos
    return obj


def add_parameter_definitions(template: Dict[str, Any],
                              literal_to_param: Dict[str, str]) -> None:
    """
    A partir de literal_to_param = { "<literal>": "NombreParametro", ... },
    asegura que en template["parameters"] exista una definición para cada
    "NombreParametro" (si no existe ya).

    - type: "String"
    - defaultValue: valor literal original (se sobreescribirá luego por
      overwrite_parameter_defaults_with_names en el flujo principal, pero
      aquí mantenemos la traza del literal original por si es útil).

    No elimina nada, solo añade los que falten.
    """
    params = template.setdefault("parameters", {})
    if not isinstance(params, dict):
        # Si por lo que sea no es un dict, no hacemos nada
        return

    for literal, pname in literal_to_param.items():
        if not pname:
            continue
        if pname in params and isinstance(params[pname], dict):
            # Ya existe, no lo pisamos
            continue

        # Creamos una definición básica de parámetro
        params[pname] = {
            "type": "String",
            "defaultValue": literal
        }
