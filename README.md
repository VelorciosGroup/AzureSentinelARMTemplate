AzureSentinelARMTemplate

Repositorio para la automatización de playbooks de Azure Sentinel y plantillas ARM, incluyendo integración con Sophos y CrowdStrike.

---

Contenido del Repositorio

- Sophos_prueba_final/
  Contiene playbooks de Sophos listos para deploy y un directorio output/ con los resultados transformados.

- python_app/
  Aplicación en Python para automatizar la creación y transformación de plantillas y playbooks.
  - src/ → Código fuente de la aplicación.
  - examples/ → Ejemplos de playbooks y plantillas listas para probar.
  - requirements.txt → Dependencias necesarias para ejecutar la aplicación.
  - resultado.json → Ejemplo de salida generada por la aplicación.

- script-automate-templates.ps1
  Script de PowerShell para ejecutar la automatización de plantillas.

---

Descripción

Este repositorio permite:

- Aplicar una plantilla maestra sobre un conjunto de playbooks JSON.
- Generar automáticamente la salida transformada en un directorio de output.
- Mantener ejemplos separados de Sophos y CrowdStrike para pruebas.
- Automatizar despliegues de plantillas ARM y playbooks en Azure Sentinel.

---

Instalación

1. Clonar el repositorio:

git clone <url-del-repositorio>
cd AzureSentinelARMTemplate/python_app

2. Crear un entorno virtual (recomendado):

python3 -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows

3. Instalar dependencias:

pip install -r requirements.txt

4. Instalar el módulo template_automation (opcional si quieres usarlo como paquete):

cd src/template_automation
pip install -e .

---

Uso

Desde línea de comandos

python3 -m template_automation -master <ruta_master.json> -dirin <directorio_playbooks> -dirout <directorio_salida> [-v]

Opciones:

- -master, -m → Ruta al JSON de plantilla maestra.
- -dirin, -i → Directorio que contiene los playbooks de entrada.
- -dirout, -o → Directorio donde se escribirá la salida transformada.
- -v → Incrementa el nivel de verbosidad (-v, -vv, etc.).

Ejemplo:

python3 -m template_automation -m examples/Sophos_prueba_final/deploy.json -i examples/Sophos_prueba_final -o output

PowerShell

Se puede ejecutar directamente con el script:

.\script-automate-templates.ps1 -Master "examples/Sophos_prueba_final/deploy.json" -DirIn "examples/Sophos_prueba_final" -DirOut "output"

---

Estructura de los Directorios

AzureSentinelARMTemplate/
├─ Sophos_prueba_final/        # Playbooks Sophos
│  ├─ output/                  # Playbooks generados
├─ python_app/
│  ├─ examples/                # Ejemplos de Sophos y CrowdStrike
│  ├─ src/                     # Código fuente de la aplicación
│  └─ requirements.txt
├─ script-automate-templates.ps1
└─ Button.png                  # Imagen del proyecto

---

Contribuciones

1. Crear una rama nueva para tus cambios.
2. Hacer commit y push a tu rama.
3. Abrir un Pull Request describiendo los cambios.

---

Licencia

Este repositorio es propiedad del autor y su uso está sujeto a las políticas internas de la organización.

---

Notas

- Todos los archivos en examples/ se pueden usar como referencia de la estructura esperada.
- Los playbooks generados en output/ son independientes y se pueden desplegar en Azure Sentinel directamente.
