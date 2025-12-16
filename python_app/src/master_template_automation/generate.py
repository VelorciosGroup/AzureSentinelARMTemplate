import json
import re
import os

def generate_master(playbooks, dependsOn, dirin):
    """
    Genera una Master Template en formato JSON a partir de múltiples playbooks, incluyendo sus
    parámetros y dependencias, y la guarda en un directorio de salida.

    La plantilla resultante está lista para ser desplegada en Azure y contiene:
    - Esquema y versión de contenido.
    - Parámetros globales (como el nombre del cliente y parámetros de KeyVault).
    - Recursos de despliegue (cada playbook como un recurso independiente).
    - Salidas con instrucciones post-despliegue y notas de API.

    :param playbooks: Diccionario donde la clave es el nombre del playbook y el valor es otro diccionario
                      con los parámetros y sus valores por defecto.
                      Ejemplo:
                      {
                          "Playbook1": {"param1": {"defaultValue": "valor1", "type": "string"}, ...},
                          "Playbook2": {...}
                      }
    :param dependsOn: Diccionario que contiene las dependencias de cada playbook.
                      Ejemplo:
                      {
                          "Playbook1": ["Playbook2", "Playbook3"],
                          ...
                      }
    :param dirin: Ruta del directorio donde se guardará el archivo de salida "deploy.json".
    :return: None. La función genera el archivo JSON directamente en el disco.
    """
    print("Generando plantilla base sobre la que trabajar")
    
    # Plantilla base con esquema, versión y secciones iniciales
    template_base = {
        "$schema": "http://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
        "contentVersion": "1.0.0.0",
        "parameters": {},
        "variables": {},
        "resources": [],
        "outputs": {
            "postDeployNote": {
                "type": "string",
                "value": (
                    "✅ Despliegue completado.\n"
                    "⚠️ Ahora debes asignar permisos de comentarios a los playbooks: \n"
                    "⚫ Cliente_Enrich_Sophos_Get_Device_Info_Playbook\n"
                    "⚫ Cliente_Enrich_Sophos_Get_Recent_Alert_Info_Playbook\n"
                    "Y permisos de keyvault a los playbooks:\n"
                    "⚫ Cliente_Enrich_Sophos_Get_Recent_Alert_Info_Playbook\n"
                    "⚫ Cliente_Enrich_Sophos_Get_Device_Info_Playbook\n"
                    "⚫ Cliente_OrchestatorPart_Sophos_Block_IOC_Playbook\n"
                    "⚫ Cliente_Action_Sophos_Launch_Antivirus_Playbook\n"
                    "⚫ Cliente_Action_Sophos_Device_Isolation_Playbook\n"
                    "⚫ Cliente_Action_Sophos_Block_IP_Playbook\n"
                )
            },
            "postDeployApiTagInstructions": {
                "type": "string",
                "value": (
                    "Para asignar correctamente el tag en las policy ⚠️: Acceder a Sophos Central → Mis productos → "
                    "Endpoint → Policy → Configuración → Añadir nuevo. En el campo \"Etiqueta de sitio web\" hay "
                    "que poner el tag escogido en el despliegue y en el campo \"Acción\" hay que poner la opción de bloquear"
                )
            }
        }
    }

    # ========================= Generación de recursos por playbook =========================
    for playbook in playbooks:
        print(f"Añadiendo playbook {playbook} a la plantilla base")

        # Estructura base de un recurso de tipo playbook
        playbookpayload = {
            "type": "Microsoft.Resources/deployments",
            "apiVersion": "2025-03-01",
            "name": "",
            "dependsOn": [],
            "properties": {
                "mode": "Incremental",
                "templateLink": {
                    "uri": "",
                    "contentVersion": "1.0.0.0"
                },
                "parameters": {}
            }
        }

        # Nombre del playbook
        print("Añadiendo nombre de playbook como parámetro")
        playbookpayload["name"] = playbook

        # ========================= Añadir parámetros al playbook =========================
        print("Añadiendo resto de parámetros")
        for param in playbooks[playbook]:
            # Patrones para detectar tipos especiales de parámetros
            pattern1 = r"workflows_(.*)_name"
            pattern2 = r"workflows_(.*)_externalid"
            pattern3 = r"connections_keyvault(.*)_externalid"
            pattern4 = r"connections_(.*)_externalid"

            match1 = re.search(pattern1, param)
            match2 = re.search(pattern2, param)
            match3 = re.search(pattern3, param)
            match4 = re.search(pattern4, param)

            if match1:
                playbookpayload['properties']['parameters'][param] = {
                    "value": f"[concat(parameters('client_Name'), '_{playbooks[playbook][param]['defaultValue']}')]"
                }
            elif match2:
                playbookpayload["properties"]['parameters'][param] = {
                    "value": f"[concat(parameters('client_Name'), '_{match2.group(1)}')]"
                }
            elif match3:
                playbookpayload["properties"]["parameters"]["keyvault_Name"] = {
                    "value": "[parameters('keyvault_Name_Pack')]"
                }
            elif match4:
                playbookpayload["properties"]["parameters"][param] = {
                    "value": playbooks[playbook][param]['defaultValue']
                }
            else:
                playbookpayload['properties']['parameters'][param] = {
                    "value": f"[parameters('{param}_Pack')]"
                }

        # ========================= Añadir dependencias =========================
        print("Añadiendo dependencias (workflows)")
        for file in dependsOn:
            if file == playbookpayload["name"]:
                for dependency in dependsOn[file]:
                    playbookpayload['dependsOn'].append(dependency)

        # Añadir el playbook como recurso en la plantilla
        template_base['resources'].append(playbookpayload)

    # ========================= Añadir parámetros globales =========================
    print("Añadiendo parámetros a la master template")
    template_base["parameters"] = {
        "client_Name": {
            "defaultValue": "CLIENTE",
            "type": "string"
        }
    }

    # Parametrización de los parámetros individuales de cada playbook
    for playbook in playbooks:
        for param in playbooks[playbook]:
            pattern1 = r"workflows_(.*)_name"
            pattern2 = r"connections(.*)_externalid"
            pattern3 = r"workflows_(.*)_externalid"
            pattern4 = r"connections_keyvault(.*)_externalid"

            match1 = re.search(pattern1, param)
            match2 = re.search(pattern2, param)
            match3 = re.search(pattern3, param)
            match4 = re.search(pattern4, param)

            if not match1 and not match2 and not match3 and not match4 and param not in template_base["parameters"]:
                template_base["parameters"][f"{param}_Pack"] = playbooks[playbook][param]

            if match4:
                template_base["parameters"]["keyvault_Name_Pack"] = {
                    "defaultValue": "MSSP-Desarrollo-SOC",
                    "type": "string"
                }

    # ========================= Guardar plantilla en disco =========================
    outputfolder = os.path.join(dirin, "output")
    os.makedirs(outputfolder, exist_ok=True)

    outputfile = os.path.join(outputfolder, "deploy.json")
    with open(outputfile, "w", encoding="utf-8") as writefile:
        print("Convierte a json la master template")
        json.dump(template_base, writefile, indent=4)
