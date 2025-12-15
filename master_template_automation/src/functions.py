import re
from pathlib import Path

def normalizeFileNames(archivo):
    file_name = Path(archivo).name
    path = Path(archivo)
    
    file_name = re.sub(r"automation", "OrchestatorPart", file_name, flags=re.IGNORECASE)
    file_name_array = file_name.split("_", 1)
    if file_name_array[1].startswith("OrchestatorPart") or file_name_array[1].startswith("Action") or file_name_array[1].startswith("Enrich"):
        file_name = file_name_array[1]
    if not file_name.endswith("_Playbook.json"):
        file_name = file_name.replace(".json", "_Playbook.json")
    newpath = path.with_name(file_name)
    path.rename(newpath)
    print(f"Normalizando nombre de archivo a: {file_name} y cambiando ruta")
    return newpath


def deleteprefix(archivo):
    with open(archivo, "r") as input:
        lines = input.readlines()
    
    pattern = r"\"workflows_(.*)_(name|externalid)\": {"
    patternAutomation = r"Automation"
    for index, _ in enumerate(lines):
        lines[index] = re.sub(patternAutomation, "OrchestatorPart", lines[index])
    for line in lines:
        match = re.search(pattern, line)
        if match:
            playbook = match.group(1)
            name_list = playbook.split("_", 1)
            if name_list[1].startswith("OrchestatorPart") or name_list[1].startswith("Action") or name_list[1].startswith("Enrich") or name_list[1].startswith("Automation"):
                playbook = name_list[1]
            if playbook.endswith("_playbook"):
                playbook = playbook.replace("_playbook", "_Playbook")
            if not playbook.endswith("_Playbook"):
                playbook = playbook + "_Playbook"
            for index, _ in enumerate(lines):
                lines[index] = re.sub(match.group(1), playbook, lines[index])

    with open(archivo, "w") as output:
        output.writelines(lines)