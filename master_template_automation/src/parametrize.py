import json
import re
import os

# ----------------------------------------- PARAMETERS -----------------------------------------


def searchKeyvaultParams(lines):
    """
    Revisa las lineas pasadas por parámetros pertenecientes al fichero que se está leyendo
    y saca los parámetros de keyvault que hagan falta. Por ejemplo,
    para sophos: clientID, clientSecret
    para crowdstrike: clientID, clientSecret, BaseUrl
    
    :param lines: Description
    """
    # Creo un patrón con regex para buscar las variables que se usan de keyvault
    # ClientId, ClientSecret ... vienen dentro de  "path": "/secrets/@{encodeURIComponent(variables('ClientID'))}/value"
    pattern = r"/secrets/@{encodeURIComponent\((variables|parameters)\('([^']+)'\)"

    matches = []

    # busco el patrón por todas las lineas
    for line in lines:
        match = re.search(pattern, line)
        if match:
            matches.append(f"keyvault_{match.group(2)}")
    
    return matches
            


def parametrizeFiles(files):
    print("Parametrizando archivos añadidos")
    params_for_file = {}
    for file in files:
        print(f"\n\nParámetros para el archivo {os.path.basename(file)}:")
        #añado el nombre del playbook
        filename = os.path.basename(file)
        filename = os.path.splitext(filename)[0] # le quito la extensión .json

        params_for_file[filename] = {}
        with open(file, "r") as read_file:
            lines = read_file.readlines()
            keyvault_params = {}
            keyvault_params[filename] = searchKeyvaultParams(lines)

        
        json_string = "".join(lines)
        data = json.loads(json_string)

        for param in data['parameters']:
            
            # introduzco todos los parámetros en params_for_file
            params_for_file[filename][param] = data['parameters'][param]
            print(data['parameters'][param]['defaultValue'])

            # introduzco los parámetros de keyvault dentro de params_for_file
            if len(keyvault_params[filename]) > 0:
                for item in keyvault_params[filename]:
                    params_for_file[filename][item] = {
                        "defaultValue": f"Rellenar_{item}",
                        "type": "string"
                    }
        
        

    # retorno la variable con todos los parámetros
    return params_for_file


# ----------------------------------------- DEPENDS ON -----------------------------------------


def searchDependsOn(lines):
    print("Buscando dependencias en archivos (workflows)")

    matches = []
    
    # El patrón será el nombre del playbook que va entre workflows_ y _externalid
    pattern = r"workflows_(.*)_externalid"

    for line in lines:
        match = re.search(pattern, line)

        if match and match.group(1) not in matches:
            print(f"Dependencia encontrada: {match.group(1)}")
            matches.append(match.group(1))
            
    return matches


def parametrizeDependsOn(files):
    dependsOn = {}


    for file in files:
        
        filename = os.path.basename(file)
        filename = os.path.splitext(filename)[0] # le quito la extensión .json

        dependsOn[filename] = {}
        with open(file, "r") as file:
            lines = file.readlines()
            dependsOn[filename] = searchDependsOn(lines)

    return dependsOn