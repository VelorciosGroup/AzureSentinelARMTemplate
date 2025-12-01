import json
from typing import Any, Dict

def replace_substrings(obj: Any, mapping: Dict[str, str]) -> Any:
    """
    Reemplaza substrings en cualquier string del árbol JSON.

    mapping: { "parameters('viejo')" : "parameters('nuevo')", ... }

    Se usa para actualizar referencias a parámetros ya existentes,
    por ejemplo cuando renombramos 'workflows_...' -> 'CambioDeNombre'.
    """
    if isinstance(obj, dict):
        return {k: replace_substrings(v, mapping) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [replace_substrings(item, mapping) for item in obj]
    elif isinstance(obj, str):
        new_s = obj
        for old, new in mapping.items():
            if old in new_s:
                new_s = new_s.replace(old, new)
        return new_s
    else:
        return obj

def collect_string_literals(obj: Any, counts: Dict[str, int]) -> None:
    """
    Recorre recursivamente el JSON y cuenta cuántas veces aparece cada string.
    """
    if isinstance(obj, dict):
        for v in obj.values():
            collect_string_literals(v, counts)
    elif isinstance(obj, list):
        for item in obj:
            collect_string_literals(item, counts)
    elif isinstance(obj, str):
        counts[obj] = counts.get(obj, 0) + 1


def replace_literals(obj: Any, literal_to_param: Dict[str, str]) -> Any:
    """
    Reemplaza en todo el árbol JSON los literales seleccionados por
    [parameters('<nombre_param>')].
    """
    if isinstance(obj, dict):
        return {k: replace_literals(v, literal_to_param) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [replace_literals(item, literal_to_param) for item in obj]
    elif isinstance(obj, str):
        param = literal_to_param.get(obj)
        if param:
            return f"[parameters('{param}')]"
        return obj
    else:
        return obj


def ensure_parameters_block(template: Dict[str, Any]) -> None:
    """
    Asegura que el template tiene un bloque 'parameters' dict en la raíz.
    """
    if "parameters" not in template or not isinstance(template["parameters"], dict):
        template["parameters"] = {}


def add_parameter_definitions(
    template: Dict[str, Any],
    literal_to_param: Dict[str, str]
) -> None:
    """
    Añade definiciones de parámetros en template['parameters'] para cada
    literal -> nombre_param.

    Comportamiento especial:
      - Si el parámetro YA existe y su nombre empieza por 'workflow' o
        'workflows', NO se crea uno nuevo, sino que se ACTUALIZA su
        defaultValue con el literal original.

      - Si el parámetro NO existe, se crea normalmente:
        {
          "type": "String",
          "defaultValue": "<literal>"
        }
    """
    ensure_parameters_block(template)
    params_block = template["parameters"]

    for literal, pname in literal_to_param.items():
        # Si ya existe un parámetro con ese nombre
        if pname in params_block:
            # Caso especial: parámetros de workflows (playbooks de Sentinel)
            if pname.startswith("workflow"):
                # Aseguramos que es un dict
                if not isinstance(params_block[pname], dict):
                    params_block[pname] = {}
                # Actualizamos defaultValue al literal original
                params_block[pname]["defaultValue"] = literal
            # Si existe pero no empieza por workflow*, lo dejamos tal cual
            continue

        # Si NO existe, lo creamos normalmente
        params_block[pname] = {
            "type": "String",
            "defaultValue": literal
        }

    template["parameters"] = params_block
