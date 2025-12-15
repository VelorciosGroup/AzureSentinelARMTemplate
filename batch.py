import os
import sys
import json

playbooks = [
    "Cliente_Action_Sophos_Block_Domain_Alert_Playbook",
    "Cliente_Action_Sophos_Block_Domain_Entity_Playbook",
    "Cliente_Action_Sophos_Block_Domain_Incident_Playbook"
]

def main():
    if len(sys.argv) != 2:
        print("Uso: python crear_playbooks_json.py <directorio_destino>")
        sys.exit(1)

    output_dir = sys.argv[1]

    os.makedirs(output_dir, exist_ok=True)

    for name in playbooks:
        file_path = os.path.join(output_dir, f"{name}.json")

        if os.path.exists(file_path):
            print(f"Ya existe: {file_path}")
            continue

        contenido = {
            "name": name,
            "type": "playbook",
            "status": "placeholder",
            "description": "Archivo creado automáticamente",
            "version": 1
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(contenido, f, indent=4, ensure_ascii=False)

        print(f"Creado: {file_path}")

    print("\nTodos los archivos han sido procesados.")

if __name__ == "__main__":
    main()
