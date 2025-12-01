import json
import re
import argparse
from pathlib import Path

# Detecta valores que conviene parametrizar
def es_parametrizable(valor):
    if not isinstance(valor, str):
        return False
    patrones = [
        r"^/subscriptions/.+",
        r"ClientID",
        r"ClientSecret",
        r"BaseURL",
        r"BaseUrl",
        r"Secret",
        r"-Crowdstrike",
        r"keyvault",
        r"workspace",
        r"resourceGroups",
    ]
    return any(re.search(p, valor, re.IGNORECASE) for p in patrones)

# Añade un parámetro y devuelve el nombre final
def agregar_parametro(template, nombre, valor_original):
    if nombre in template["parameters"]:
        return nombre

    template["parameters"][nombre] = {
        "type": "string",
        "defaultValue": valor_original
    }
    return nombre

# Recorre recursivamente el JSON
def procesar_nodos(template, nodo, path=""):
    if isinstance(nodo, dict):
        for k, v in nodo.items():
            nueva_ruta = f"{path}.{k}" if path else k

            if isinstance(v, str) and es_parametrizable(v):
                param_name = k.replace("-", "_").replace(" ", "_")
                param_name = agregar_parametro(template, param_name, v)
                nodo[k] = f"[parameters('{param_name}')]"

            else:
                procesar_nodos(template, v, nueva_ruta)

    elif isinstance(nodo, list):
        for i, item in enumerate(nodo):
            procesar_nodos(template, item, f"{path}[{i}]")

def parametrizar_plantilla(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as f:
        template = json.load(f)

    if "parameters" not in template:
        template["parameters"] = {}

    procesar_nodos(template, template)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(template, f, indent=2)

    print(f"✔ Plantilla parametrizada generada en: {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parametrizador automático de plantillas ARM.")
    parser.add_argument("input", help="Plantilla ARM original")
    parser.add_argument("output", help="Archivo de salida")
    args = parser.parse_args()

    parametrizar_plantilla(args.input, args.output)
