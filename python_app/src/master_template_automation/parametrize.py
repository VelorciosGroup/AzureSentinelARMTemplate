import json
import re
import os

# ----------------------------------------- PARAMETERS -----------------------------------------

def searchKeyvaultParams(lines):
    """
    Busca los parámetros que provienen de KeyVault dentro de un conjunto de líneas de un archivo JSON.
    
    Este método detecta patrones específicos donde se utilizan variables o parámetros de KeyVault.
    Por ejemplo, si en un playbook se utiliza:
        "/secrets/@{encodeURIComponent(variables('ClientID'))}/value"
    se extraerá 'ClientID' como parámetro de KeyVault.
    
    :param lines: Lista de strings que representan las líneas de un archivo JSON.
    :return: Lista de parámetros encontrados que requieren KeyVault, con el prefijo "keyvault_".
    """
    # Patrón regex para detectar variables o parámetros dentro de la ruta de KeyVault
    pattern = r"/secrets/@{encodeURIComponent\((variables|parameters)\('([^']+)'\)"
    
    matches = []

    # Recorremos cada línea buscando coincidencias
    for line in lines:
        match = re.search(pattern, line)
        if match:
            matches.append(f"keyvault_{match.group(2)}")
    
    return matches


def parametrizeFiles(files):
    """
    Lee archivos JSON de playbooks y genera un diccionario con todos los parámetros que estos contienen,
    incluyendo los parámetros que provienen de KeyVault.

    Además, imprime en consola los parámetros encontrados y sus valores por defecto.
    
    :param files: Lista de rutas a archivos JSON de playbooks.
    :return: Diccionario con la siguiente estructura:
        {
            "nombre_playbook": {
                "parametro1": {"defaultValue": ..., "type": ...},
                "parametro2": {"defaultValue": ..., "type": ...},
                "keyvault_parametro": {"defaultValue": ..., "type": "string"},
                ...
            },
            ...
        }
    """
    print("Parametrizando archivos añadidos")
    params_for_file = {}

    for file in files:
        print(f"\n\nParámetros para el archivo {os.path.basename(file)}:")
        
        # Extraigo el nombre del archivo sin extensión
        filename = os.path.splitext(os.path.basename(file))[0]
        params_for_file[filename] = {}

        # Leo las líneas del archivo
        with open(file, "r") as read_file:
            lines = read_file.readlines()
            keyvault_params = {}
            keyvault_params[filename] = searchKeyvaultParams(lines)

        # Cargo el JSON completo para acceder a los parámetros
        json_string = "".join(lines)
        data = json.loads(json_string)

        for param in data['parameters']:
            # Agrego todos los parámetros al diccionario
            params_for_file[filename][param] = data['parameters'][param]
            print(data['parameters'][param]['defaultValue'])

            # Agrego los parámetros de KeyVault con valores por defecto
            if len(keyvault_params[filename]) > 0:
                for item in keyvault_params[filename]:
                    params_for_file[filename][item] = {
                        "defaultValue": f"Rellenar_{item}",
                        "type": "string"
                    }

    return params_for_file


# ----------------------------------------- DEPENDS ON -----------------------------------------

def searchDependsOn(lines):
    """
    Busca dependencias entre workflows dentro de un archivo JSON.
    
    Una dependencia se detecta buscando patrones que indiquen el uso de otro workflow:
        "workflows_<nombre_workflow>_externalid"
    
    :param lines: Lista de strings que representan las líneas de un archivo JSON.
    :return: Lista de nombres de workflows de los que depende el archivo.
    """
    print("Buscando dependencias en archivos (workflows)")
    matches = []

    pattern = r"workflows_(.*)_externalid"

    for line in lines:
        match = re.search(pattern, line)
        if match and match.group(1) not in matches:
            print(f"Dependencia encontrada: {match.group(1)}")
            matches.append(match.group(1))
            
    return matches


def parametrizeDependsOn(files):
    """
    Genera un diccionario con las dependencias de cada archivo JSON.
    
    :param files: Lista de rutas a archivos JSON de playbooks.
    :return: Diccionario con la siguiente estructura:
        {
            "nombre_playbook": ["dependencia1", "dependencia2", ...],
            ...
        }
    """
    dependsOn = {}

    for file in files:
        filename = os.path.splitext(os.path.basename(file))[0]
        dependsOn[filename] = {}

        # Leo el archivo para buscar dependencias
        with open(file, "r") as file:
            lines = file.readlines()
            dependsOn[filename] = searchDependsOn(lines)

    return dependsOn
