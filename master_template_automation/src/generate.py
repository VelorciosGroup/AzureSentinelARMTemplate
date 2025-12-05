import json
import os


def generate_master(playbooks, dependsOn):
    template_base = {
        "$schema": "http://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
        "contentVersion": "1.0.0.0",
        "parameters": {},
        "variables": {},
        "resources": [],
        
        "outputs": {
            "postDeployNote": {
                "type": "string",
                "value": "✅ Despliegue completado.\n⚠️ Ahora debes asignar permisos de comentarios a los playbooks: \n⚫ Cliente_Enrich_Sophos_Get_Device_Info_Playbook\n⚫ Cliente_Enrich_Sophos_Get_Recent_Alert_Info_Playbook\nY permisos de keyvault a los playbooks:\n⚫ Cliente_Enrich_Sophos_Get_Recent_Alert_Info_Playbook\n⚫ Cliente_Enrich_Sophos_Get_Device_Info_Playbook\n⚫ Cliente_OrchestatorPart_Sophos_Block_IOC_Playbook\n⚫ Cliente_Action_Sophos_Launch_Antivirus_Playbook\n⚫ Cliente_Action_Sophos_Device_Isolation_Playbook\n⚫ Cliente_Action_Sophos_Block_IP_Playbook\n"
            },
            "postDeployApiTagInstructions": {
                "type": "string",
                "value": "Para asignar correctamente el tag en las policy ⚠️: Acceder a Sophos Central → Mis productos → Endpoint → Policy → Configuración → Añadir nuevo. En el campo \"Etiqueta de sitio web\" hay que poner el tag escogido en el despliegue y en el campo \"Acción\" hay que poner la opción de bloquear"
            }
	    }
    }

    for playbook in playbooks:

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
				"parameters": {
					
				}
			}
        }

        # añador el nombre del playbook
        playbookpayload["name"] = playbook

        # añado los parámetros
        for param in playbooks[playbook]:
            
            playbookpayload['properties']['parameters'][param] = {
                "value": playbooks[playbook][param]['defaultValue']
            }


        # añado las dependencias
        for file in dependsOn:
            if file == playbookpayload["name"]:
                for dependencies in dependsOn[file]:
                    playbookpayload['dependsOn'] = dependencies
                    
        # añado la declaración del playbook a resources
        template_base['resources'].append(playbookpayload)


    with open("./resultado.json", "w", encoding="utf-8") as writefile:
        json.dump(template_base, writefile, indent=4)