import subprocess
import sys
from pathlib import Path
import os
import master_template_automation.gui as gui

def main():
    """
    Script principal que lanza la GUI para seleccionar playbooks, genera la Master Template
    y ejecuta el módulo de automatización de plantillas.

    Flujo de ejecución:
    1. Lanza la GUI para seleccionar archivos JSON de playbooks.
    2. Obtiene el directorio de entrada donde se encuentran los archivos seleccionados.
    3. Define rutas y nombres de salida para la Master Template.
    4. Ejecuta el módulo `template_automation.__main__` usando subprocess para mantener los imports relativos.
    """
    # ========================= Lanzar GUI =========================
    dirin = gui.rendergui()
    print(f"Directorio de entrada: {dirin}")

    if not dirin:
        print("No se seleccionaron archivos, saliendo...")
        sys.exit(1)

    # ========================= Configuración de rutas =========================
    BASE_DIR = Path(__file__).resolve().parent  # directorio donde se encuentra este script

    TEMPLATE_AUTOMATION_MODULE = "template_automation.__main__"  # módulo a ejecutar

    dirout = os.path.join(dirin, "output")  # directorio de salida
    master = os.path.join(dirout, "deploy.json")  # ruta de la Master Template

    # ========================= Ejecutar módulo de automatización =========================
    # Se utiliza subprocess.run para ejecutar el módulo como CLI, preservando imports relativos
    subprocess.run(
        [
            sys.executable,  # intérprete de Python actual
            "-m", TEMPLATE_AUTOMATION_MODULE,
            "-m", master,  # Master Template generada
            "-i", dirin,   # Directorio de entrada
            "-o", dirout   # Directorio de salida
        ],
        cwd=BASE_DIR / "template_automation/src"  # carpeta raíz para que los imports relativos funcionen
    )


if __name__ == "__main__":
    main()
