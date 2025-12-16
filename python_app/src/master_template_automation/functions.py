import re
from pathlib import Path

def normalize_file_names(file_path):
    """
    Normalizes the name of a playbook JSON file and renames it on disk.

    Features:
    - Replaces the word 'automation' with 'OrchestatorPart' in the filename.
    - Removes unnecessary prefixes before 'OrchestatorPart', 'Action', or 'Enrich'.
    - Ensures the filename ends with "_Playbook.json".
    - Renames the file at its original location.

    :param file_path: Path to the file to normalize (str or Path).
    :return: The new normalized file path (Path).
    """
    file_name = Path(file_path).name
    path = Path(file_path)
    
    # Replace "automation" with "OrchestatorPart" (case-insensitive)
    file_name = re.sub(r"automation", "OrchestatorPart", file_name, flags=re.IGNORECASE)
    
    # Remove unnecessary prefixes before 'OrchestatorPart', 'Action', or 'Enrich'
    file_name_array = file_name.split("_", 1)
    if file_name_array[1].startswith(("OrchestatorPart", "Action", "Enrich")):
        file_name = file_name_array[1]
    
    # Ensure the correct suffix
    if not file_name.endswith("_Playbook.json"):
        file_name = file_name.replace(".json", "_Playbook.json")
    
    # Rename the file on disk
    new_path = path.with_name(file_name)
    path.rename(new_path)
    print(f"Normalized file name to: {file_name} and updated path")
    return new_path


def remove_prefixes(file_path):
    """
    Cleans and normalizes workflow references inside a playbook JSON file.

    Features:
    - Replaces the word 'Automation' with 'OrchestatorPart' in the file content.
    - Adjusts playbook names to remove unnecessary prefixes.
    - Ensures names end with "_Playbook".

    :param file_path: Path to the JSON file to process (str or Path).
    :return: None. Modifies the file directly on disk.
    """
    # Read all lines from the file
    with open(file_path, "r") as input_file:
        lines = input_file.readlines()
    
    # Search patterns
    workflow_pattern = r"\"workflows_(.*)_(name|externalid)\": {"
    automation_pattern = r"Automation"

    # Replace "Automation" with "OrchestatorPart" in all lines
    for index, _ in enumerate(lines):
        lines[index] = re.sub(automation_pattern, "OrchestatorPart", lines[index])

    # Normalize workflow names found
    for line in lines:
        match = re.search(workflow_pattern, line)
        if match:
            playbook_name = match.group(1)
            name_list = playbook_name.split("_", 1)
            if name_list[1].startswith(("OrchestatorPart", "Action", "Enrich", "Automation")):
                playbook_name = name_list[1]
            
            # Ensure correct suffix
            if playbook_name.endswith("_playbook"):
                playbook_name = playbook_name.replace("_playbook", "_Playbook")
            if not playbook_name.endswith("_Playbook"):
                playbook_name += "_Playbook"

            # Replace old name with new one in all lines
            for index, _ in enumerate(lines):
                lines[index] = re.sub(match.group(1), playbook_name, lines[index])

    # Write changes back to the file
    with open(file_path, "w") as output_file:
        output_file.writelines(lines)
