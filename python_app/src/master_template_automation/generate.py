import json
import re
import os

def generate_master(playbooks, dependencies_dict, input_dir):
    """
    Generates a Master Template in JSON format from multiple playbooks, including their
    parameters and dependencies, and saves it to an output directory.

    The resulting template is ready to deploy on Azure and contains:
    - Schema and content version.
    - Global parameters (like client name and KeyVault parameters).
    - Deployment resources (each playbook as an independent resource).
    - Outputs with post-deployment instructions and API notes.

    :param playbooks: Dictionary where the key is the playbook name and the value is another dictionary
                      with parameters and their default values.
                      Example:
                      {
                          "Playbook1": {"param1": {"defaultValue": "value1", "type": "string"}, ...},
                          "Playbook2": {...}
                      }
    :param dependencies_dict: Dictionary containing the dependencies of each playbook.
                              Example:
                              {
                                  "Playbook1": ["Playbook2", "Playbook3"],
                                  ...
                              }
    :param input_dir: Path to the directory where the output file "deploy.json" will be saved.
    :return: None. The function generates the JSON file directly on disk.
    """
    print("Generating base template to work with")
    
    # Base template with schema, version, and initial sections
    master_template = {
        "$schema": "http://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
        "contentVersion": "1.0.0.0",
        "parameters": {},
        "variables": {},
        "resources": [],
        "outputs": {
            "postDeployNote": {
                "type": "string",
                "value": (
                    "✅ Deployment completed.\n"
                    "⚠️ Now you must assign comment permissions to the playbooks: \n"
                    "⚫ Client_Enrich_Sophos_Get_Device_Info_Playbook\n"
                    "⚫ Client_Enrich_Sophos_Get_Recent_Alert_Info_Playbook\n"
                    "And KeyVault permissions to the playbooks:\n"
                    "⚫ Client_Enrich_Sophos_Get_Recent_Alert_Info_Playbook\n"
                    "⚫ Client_Enrich_Sophos_Get_Device_Info_Playbook\n"
                    "⚫ Client_OrchestatorPart_Sophos_Block_IOC_Playbook\n"
                    "⚫ Client_Action_Sophos_Launch_Antivirus_Playbook\n"
                    "⚫ Client_Action_Sophos_Device_Isolation_Playbook\n"
                    "⚫ Client_Action_Sophos_Block_IP_Playbook\n"
                )
            },
            "postDeployApiTagInstructions": {
                "type": "string",
                "value": (
                    "To correctly assign the tag in policies ⚠️: Go to Sophos Central → My Products → "
                    "Endpoint → Policy → Settings → Add new. In the \"Website Tag\" field, enter the tag "
                    "selected during deployment and in the \"Action\" field choose the 'block' option."
                )
            }
        }
    }

    # ========================= Generate resources per playbook =========================
    for playbook_name in playbooks:
        print(f"Adding playbook {playbook_name} to the base template")

        # Base structure of a playbook resource
        playbook_resource = {
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

        # Set the playbook name
        print("Adding playbook name as parameter")
        playbook_resource["name"] = playbook_name

        # ========================= Add parameters to the playbook =========================
        print("Adding remaining parameters")
        for param in playbooks[playbook_name]:
            # Patterns to detect special parameter types
            pattern1 = r"workflows_(.*)_name"
            pattern2 = r"workflows_(.*)_externalid"
            pattern3 = r"connections_keyvault(.*)_externalid"
            pattern4 = r"connections_(.*)_externalid"

            match1 = re.search(pattern1, param)
            match2 = re.search(pattern2, param)
            match3 = re.search(pattern3, param)
            match4 = re.search(pattern4, param)

            if match1:
                playbook_resource['properties']['parameters'][param] = {
                    "value": f"[concat(parameters('client_Name'), '_{playbooks[playbook_name][param]['defaultValue']}')]"
                }
            elif match2:
                playbook_resource["properties"]['parameters'][param] = {
                    "value": f"[concat(parameters('client_Name'), '_{match2.group(1)}')]"
                }
            elif match3:
                playbook_resource["properties"]["parameters"]["keyvault_Name"] = {
                    "value": "[parameters('keyvault_Name_Pack')]"
                }
            elif match4:
                playbook_resource["properties"]["parameters"][param] = {
                    "value": playbooks[playbook_name][param]['defaultValue']
                }
            else:
                playbook_resource['properties']['parameters'][param] = {
                    "value": f"[parameters('{param}_Pack')]"
                }

        # ========================= Add dependencies =========================
        print("Adding workflow dependencies")
        for file_name in dependencies_dict:
            if file_name == playbook_resource["name"]:
                for dependency in dependencies_dict[file_name]:
                    playbook_resource['dependsOn'].append(dependency)

        # Add the playbook as a resource in the template
        master_template['resources'].append(playbook_resource)

    # ========================= Add global parameters =========================
    print("Adding parameters to the master template")
    master_template["parameters"] = {
        "client_Name": {
            "defaultValue": "CLIENT",
            "type": "string"
        }
    }

    # Parameterize individual playbook parameters
    for playbook_name in playbooks:
        for param in playbooks[playbook_name]:
            pattern1 = r"workflows_(.*)_name"
            pattern2 = r"connections(.*)_externalid"
            pattern3 = r"workflows_(.*)_externalid"
            pattern4 = r"connections_keyvault(.*)_externalid"

            match1 = re.search(pattern1, param)
            match2 = re.search(pattern2, param)
            match3 = re.search(pattern3, param)
            match4 = re.search(pattern4, param)

            if not match1 and not match2 and not match3 and not match4 and param not in master_template["parameters"]:
                master_template["parameters"][f"{param}_Pack"] = playbooks[playbook_name][param]

            if match4:
                master_template["parameters"]["keyvault_Name_Pack"] = {
                    "defaultValue": "MSSP-Development-SOC",
                    "type": "string"
                }

    # ========================= Save template to disk =========================
    output_folder = os.path.join(input_dir, "output")
    os.makedirs(output_folder, exist_ok=True)

    output_file = os.path.join(output_folder, "deploy.json")
    with open(output_file, "w", encoding="utf-8") as writefile:
        print("Converting master template to JSON")
        json.dump(master_template, writefile, indent=4)
