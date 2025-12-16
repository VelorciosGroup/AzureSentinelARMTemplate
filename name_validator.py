import os
import json
import sys

def validar_nombres(carpeta):
    errores = []

    for archivo in os.listdir(carpeta):
        if archivo.endswith(".json"):
            ruta = os.path.join(carpeta, archivo)
            nombre_archivo = archivo.rsplit(".", 1)[0]

            with open(ruta, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    errores.append(f"{archivo}: JSON inválido")
                    continue

                parameters = data.get("parameters", {})
                encontrado = False

                for key, valor in parameters.items():
                    if key.startswith("workflows_") and key.endswith("_name"):
                        default_value = valor.get("defaultValue", "")

                        # Comparar defaultValue con nombre de archivo
                        if nombre_archivo != default_value:
                            errores.append(f"{archivo}: defaultValue '{default_value}' NO coincide con nombre de archivo '{nombre_archivo}'")

                        # Comparar clave (sin prefijo y sufijo) con nombre de archivo
                        clave_sin_prefijo = key[len("workflows_"):-len("_name")]
                        if clave_sin_prefijo != nombre_archivo:
                            errores.append(f"{archivo}: clave '{key}' NO coincide con nombre de archivo '{nombre_archivo}'")

                        encontrado = True
                        break

                if not encontrado:
                    errores.append(f"{archivo}: no se encontró clave workflow *_name")

    if errores:
        print("Se encontraron inconsistencias:")
        for e in errores:
            print(f" - {e}")
    else:
        print("Todos los archivos cumplen con la convención de nombres.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python validar_nombres.py <carpeta_json>")
        sys.exit(1)

    carpeta_json = sys.argv[1]
    validar_nombres(carpeta_json)