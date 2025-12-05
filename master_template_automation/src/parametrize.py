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
    pattern = r"/secrets/@{encodeURIComponent\(variables\('([^']+)'\)"

    matches = []

    # busco el patrón por todas las lineas
    for line in lines:
        match = re.search(pattern, line)
        if match:
            matches.append(f"keyvault_{match.group(1)}")
    
    return matches
            


def parametrizeFiles(files):
    params_for_file = {}
    for file in files:
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

                # introduzco los parámetros de keyvault dentro de params_for_file
                if len(keyvault_params[filename]) > 0:
                    for item in keyvault_params[filename]:
                        params_for_file[filename][item] = {
                            "defaultValue": f"[parameters('{item}_Pack')]",
                            "type": "string"
                        }

    # retorno la variable con todos los parámetros
    return params_for_file


# ----------------------------------------- DEPENDS ON -----------------------------------------


def searchDependsOn(lines):

    matches = []
    
    # El patrón será el nombre del playbook que va entre workflows_ y _externalid
    pattern = r"workflows_(.*)_externalid"

    for line in lines:
        match = re.search(pattern, line)

        if match and match.group(1) not in matches:
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

