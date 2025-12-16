import re
from pathlib import Path

def normalizeFileNames(archivo):
    """
    Normaliza el nombre de un archivo JSON de playbook y renombra el archivo en disco.

    Funcionalidades:
    - Reemplaza la palabra 'automation' por 'OrchestatorPart' en el nombre del archivo.
    - Quita prefijos innecesarios antes de 'OrchestatorPart', 'Action' o 'Enrich'.
    - Asegura que el archivo termine con "_Playbook.json".
    - Renombra el archivo en la ruta original.

    :param archivo: Ruta del archivo a normalizar (str o Path).
    :return: La nueva ruta del archivo normalizado (Path).
    """
    file_name = Path(archivo).name
    path = Path(archivo)
    
    # Reemplazo de "automation" por "OrchestatorPart" (case-insensitive)
    file_name = re.sub(r"automation", "OrchestatorPart", file_name, flags=re.IGNORECASE)
    
    # Quita prefijos antes de 'OrchestatorPart', 'Action' o 'Enrich'
    file_name_array = file_name.split("_", 1)
    if file_name_array[1].startswith(("OrchestatorPart", "Action", "Enrich")):
        file_name = file_name_array[1]
    
    # Asegura el sufijo correcto
    if not file_name.endswith("_Playbook.json"):
        file_name = file_name.replace(".json", "_Playbook.json")
    
    # Renombra el archivo en disco
    newpath = path.with_name(file_name)
    path.rename(newpath)
    print(f"Normalizando nombre de archivo a: {file_name} y cambiando ruta")
    return newpath


def deleteprefix(archivo):
    """
    Limpia y normaliza las referencias de workflows dentro de un archivo JSON de playbook.

    Funcionalidades:
    - Reemplaza la palabra 'Automation' por 'OrchestatorPart' dentro del contenido.
    - Ajusta los nombres de playbooks para eliminar prefijos innecesarios.
    - Asegura que los nombres terminen con "_Playbook".

    :param archivo: Ruta del archivo JSON a procesar (str o Path).
    :return: None. Modifica el archivo directamente en disco.
    """
    # Leer todas las líneas del archivo
    with open(archivo, "r") as input_file:
        lines = input_file.readlines()
    
    # Patrones de búsqueda
    pattern = r"\"workflows_(.*)_(name|externalid)\": {"
    patternAutomation = r"Automation"

    # Reemplazo de "Automation" por "OrchestatorPart" en todas las líneas
    for index, _ in enumerate(lines):
        lines[index] = re.sub(patternAutomation, "OrchestatorPart", lines[index])

    # Normaliza los nombres de los workflows encontrados
    for line in lines:
        match = re.search(pattern, line)
        if match:
            playbook = match.group(1)
            name_list = playbook.split("_", 1)
            if name_list[1].startswith(("OrchestatorPart", "Action", "Enrich", "Automation")):
                playbook = name_list[1]
            
            # Asegura sufijo correcto
            if playbook.endswith("_playbook"):
                playbook = playbook.replace("_playbook", "_Playbook")
            if not playbook.endswith("_Playbook"):
                playbook += "_Playbook"

            # Sustituye el nombre antiguo por el nuevo en todas las líneas
            for index, _ in enumerate(lines):
                lines[index] = re.sub(match.group(1), playbook, lines[index])

    # Escribe los cambios de vuelta en el archivo
    with open(archivo, "w") as output_file:
        output_file.writelines(lines)
