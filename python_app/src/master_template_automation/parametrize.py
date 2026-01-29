import json
import re
import os

# ----------------------------------------- PARAMETERS -----------------------------------------

def search_keyvault_params(lines):
    """
    Searches for parameters coming from KeyVault within a set of lines from a JSON file.
    
    This method detects specific patterns where KeyVault variables or parameters are used.
    For example, if a playbook contains:
        "/secrets/@{encodeURIComponent(variables('ClientID'))}/value"
    it will extract 'ClientID' as a KeyVault parameter.
    
    :param lines: List of strings representing the lines of a JSON file.
    :return: List of found parameters that require KeyVault, prefixed with "keyvault_".
    """
    # Regex pattern to detect variables or parameters in the KeyVault path
    pattern = r"/secrets/@{encodeURIComponent\((variables|parameters)\('([^']+)'\)"
    
    matches = []

    # Iterate over each line looking for matches
    for line in lines:
        match = re.search(pattern, line)
        if match:
            matches.append(f"keyvault_{match.group(2)}")
    
    return matches


def parametrize_files(file_paths):
    """
    Reads JSON playbook files and generates a dictionary with all the parameters they contain,
    including parameters coming from KeyVault.

    Also prints the found parameters and their default values to the console.
    
    :param file_paths: List of paths to JSON playbook files.
    :return: Dictionary structured as follows:
        {
            "playbook_name": {
                "parameter1": {"defaultValue": ..., "type": ...},
                "parameter2": {"defaultValue": ..., "type": ...},
                "keyvault_parameter": {"defaultValue": ..., "type": "string"},
                ...
            },
            ...
        }
    """
    print("Parametrizing added files")
    params_for_file = {}

    for file_path in file_paths:
        print(f"\n\nParameters for file {os.path.basename(file_path)}:")
        
        # Extract the file name without extension
        filename = os.path.splitext(os.path.basename(file_path))[0]
        params_for_file[filename] = {}

        # Read all lines from the file
        with open(file_path, "r", encoding="utf-8") as read_file:
            lines = read_file.readlines()
            keyvault_params = {}
            keyvault_params[filename] = search_keyvault_params(lines)

        # Load the complete JSON to access parameters
        json_string = "".join(lines)
        data = json.loads(json_string)

        for param in data['parameters']:
            # Add all parameters to the dictionary
            params_for_file[filename][param] = data['parameters'][param]
            print(data['parameters'][param]['defaultValue'])

            # Add KeyVault parameters with default placeholder values
            if len(keyvault_params[filename]) > 0:
                for item in keyvault_params[filename]:
                    params_for_file[filename][item] = {
                        "defaultValue": f"Fill_{item}",
                        "type": "string"
                    }

    return params_for_file


# ----------------------------------------- DEPENDENCIES -----------------------------------------

def search_dependencies(lines):
    """
    Searches for workflow dependencies within a JSON file.
    
    A dependency is detected by looking for patterns indicating the use of another workflow:
        "workflows_<workflow_name>_externalid"
    
    :param lines: List of strings representing the lines of a JSON file.
    :return: List of workflow names that the file depends on.
    """
    print("Searching for dependencies in files (workflows)")
    matches = []

    pattern = r"workflows_(.*)_externalid"

    for line in lines:
        match = re.search(pattern, line)
        if match and match.group(1) not in matches:
            print(f"Dependency found: {match.group(1)}")
            matches.append(match.group(1))
            
    return matches


def parametrize_dependencies(file_paths):
    """
    Generates a dictionary with the dependencies of each JSON file.
    
    :param file_paths: List of paths to JSON playbook files.
    :return: Dictionary structured as follows:
        {
            "playbook_name": ["dependency1", "dependency2", ...],
            ...
        }
    """
    dependencies = {}

    for file_path in file_paths:
        filename = os.path.splitext(os.path.basename(file_path))[0]
        dependencies[filename] = {}

        # Read the file to search for dependencies
        with open(file_path, "r") as json_file:
            lines = json_file.readlines()
            dependencies[filename] = search_dependencies(lines)

    return dependencies
