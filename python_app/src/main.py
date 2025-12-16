import subprocess
import sys
from pathlib import Path
import os
import master_template_automation.gui as gui

def main():
    # Abrir GUI y obtener la carpeta de los archivos seleccionados
    dirin = gui.rendergui()
    print(f"Directorio de entrada: {dirin}")

    if not dirin:
        print("No se seleccionaron archivos, saliendo...")
        sys.exit(1)

    # Directorio del script actual
    BASE_DIR = Path(__file__).resolve().parent

    # Nombre del módulo que queremos ejecutar
    TEMPLATE_AUTOMATION_MODULE = "template_automation.__main__"

    # directorio de salida
    dirout = os.path.join(dirin, "output")

    # ruta master template
    master = os.path.join(dirout, "deploy.json")

    # Ejecutar cli.py como módulo para que los imports relativos funcionen
    subprocess.run(
        [
            sys.executable,
            "-m",
            TEMPLATE_AUTOMATION_MODULE,
            "-m", master,
            "-i", dirin,
            "-o", dirout
        ],
        cwd=BASE_DIR / "template_automation/src"  # carpeta raíz para imports
    )

if __name__ == "__main__":
    main()
