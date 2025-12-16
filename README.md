Module template_automation
==========================

Sub-modules
-----------
* template_automation.cli
* template_automation.config
* template_automation.core
* template_automation.utilsModule template_automation.config
=================================
General project configuration and constants.

Constants:
- JSON_EXTENSION (str): File extension to process (default: ".json").
- DEFAULT_OUTPUT_DIR_NAME (str): Default subdirectory name for output (default: "out").
- PROJECT_ROOT (Path): Project root directory, assuming a `src/` layout.Module template_automation.cli
==============================
Command-line interface module.

Responsibilities:
- Parse command-line arguments.
- Configure logging.
- Invoke the main processing pipeline.

Functions
---------

`build_parser() ‑> argparse.ArgumentParser`
:   Build and return the argument parser for the CLI.
    
    Returns:
        argparse.ArgumentParser: Configured parser for the `template_automation` CLI.
    
    Notes:
        The parser includes arguments for:
        - Master template JSON file
        - Input directory of playbooks
        - Output directory for transformed playbooks
        - Verbosity level

`main(argv: list[str] | None = None) ‑> int`
:   Main entry point for the CLI.
    
    Args:
        argv (list[str] | None, optional): List of command-line arguments.
            If None, `sys.argv` is used. Defaults to None.
    
    Returns:
        int: Exit code (0 for success).
    
    Notes:
        - Configures logging according to the verbosity level.
        - Executes the main automation pipeline by calling `run_automation`.Module template_automation.core
===============================

Sub-modules
-----------
* template_automation.core.master_loader
* template_automation.core.playbook_loader
* template_automation.core.transformer
* template_automation.core.writerModule template_automation.core.master_loader
=============================================
Functions to load and validate the master template.

Functions
---------

`load_master_template(path: Path) ‑> Dict[str, Any]`
:   Load a JSON master template file and return it as a dictionary.
    
    Args:
        path (Path): Path to the master template JSON file.
    
    Returns:
        Dict[str, Any]: Parsed JSON data as a dictionary.
    
    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file content is not valid JSON.
    
    Notes:
        This function also calls `validate_master_template` to perform 
        validation on the loaded data. Currently, this is a stub for future validation logic.Module template_automation.core.playbook_loader
===============================================
Functions to discover and load playbooks from a directory.

Functions
---------

`discover_playbooks(dir_in: Path) ‑> List[pathlib.Path]`
:   Discover all JSON playbooks in the given directory.
    
    Args:
        dir_in (Path): Directory to search for playbook JSON files.
    
    Returns:
        List[Path]: List of paths to the discovered playbook files.
    
    Raises:
        NotADirectoryError: If the provided path is not a valid directory.
    
    Notes:
        This function uses `iter_json_files` to iterate over JSON files
        with the extension specified in `JSON_EXTENSION`.

`load_playbook(path: Path) ‑> Dict[str, Any]`
:   Load a JSON playbook and return its contents as a dictionary.
    
    Args:
        path (Path): Path to the playbook JSON file.
    
    Returns:
        Dict[str, Any]: The parsed JSON data of the playbook.
    
    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.Module template_automation.core.transformer
===========================================
Lógica de transformación principal.

Flujo actual:

1. Carga la master template.
2. Extrae los nombres de los deployments (playbooks) de la master.
3. Para cada nombre N busca en dir_in el fichero `Cliente_N.json`.
4. Si existe:
   - Lo carga.
   - Identifica y muestra por pantalla los parámetros:
       * workflows_*_name
       * workflows_*_externalid
   - Transforma:
       * workflows_*_externalid:
           - Crea var_<workflows_*_externalid> con el resourceId del workflow.
           - Reemplaza [parameters('<param>')] por [variables('var_<param>')].
   - Manejo de conexiones:
       * Siempre crea/actualiza:
           AzureSentinelConnectionName =
             "[concat('azuresentinel-', parameters('<nombredelplaybook>'))]"
       * Si el playbook tiene algún parámetro connections_keyvault_*_externalid:
           - Crea/actualiza:
               keyvault_Connection_Name =
                 "[concat('keyvault-', parameters('<nombredelplaybook>'))]"
       * (NUEVO) En cada workflow:
           - Asegura definition.parameters.$connections (type Object + defaultValue {})
       * En cada workflow:
           - Inserta/ajusta properties.parameters.$connections.value con:
               azuresentinel (AzureSentinelConnectionName)
               keyvault (keyvault_Connection_Name), si existe.
           - Añade dependsOn a ambas conexiones si aplican.
       * Añade recursos Microsoft.Web/connections:
           - para AzureSentinelConnectionName (azuresentinel)
           - para keyvault_Connection_Name (keyvault), con AlternativeParameterValues.vaultName.
   - Además, desde la master:
       * Para cada deployment, se leen sus "properties.parameters" y cualquier
         parámetro que NO exista en el playbook se añade como:
             "<param>": {
               "type": "String",
               "defaultValue": "BORRAR_<param>"
             }
         y también en:
             resources[*].properties.definition.parameters["<param>"]
   - Y además:
       * Para cada keyvault_<Sufijo> del deployment:
           - Busca en TODO el playbook la subcadena:
               "variables('<Sufijo>')"  o  "parameters('<Sufijo>')"
           - La sustituye por:
               "parameters('keyvault_<Sufijo>')"
   - Y además (NUEVO):
       * Antes de la limpieza:
           - En cada workflow, borra entradas en $connections.value con key:
               azuresentinel-<NUMERO>  (ej: azuresentinel-1, azuresentinel-2, ...)
   - Finalmente:
       * Limpieza iterativa de parámetros no usados en el playbook:
         - Primero borra definition.parameters que no se usen fuera de definition.
         - Luego borra parámetros root que no se usen fuera de parámetros (root/definition).
         - Repite hasta que no haya más cambios.
       * Sincroniza la master:
         - Borra de properties.parameters del deployment los parámetros que ya
           no existan en el playbook resultante.

Functions
---------

`get_deployment_names_from_master(master_template: Dict[str, Any]) ‑> List[str]`
:   

`get_deployment_parameters_from_master(master_template: Dict[str, Any], deployment_name: str) ‑> Dict[str, Any] | None`
:   Devuelve el diccionario properties.parameters del deployment con nombre deployment_name
    dentro de la master template, o None si no se encuentra / no es válido.

`inspect_workflow_parameters(playbook: Dict[str, Any], source_name: str) ‑> None`
:   Muestra por pantalla workflows_*_name y workflows_*_externalid.

`run_automation(master_path: Path, dir_in: Path, dir_out: Path) ‑> None`
:   

`transform_playbook(playbook: Dict[str, Any], deployment_parameters: Optional[Dict[str, Any]]) ‑> Dict[str, Any]`
:Module template_automation.core.writer
======================================
Functions to write transformed playbooks to disk.

Functions
---------

`write_playbook(output_dir: Path, input_path: Path, playbook_data: Dict[str, Any]) ‑> pathlib.Path`
:   Write the transformed playbook to the specified output directory.
    
    The output file will use the same name as the original input file.
    
    Args:
        output_dir (Path): Directory where the playbook will be written.
        input_path (Path): Original path of the input playbook (used for naming).
        playbook_data (Dict[str, Any]): The transformed playbook data to write.
    
    Returns:
        Path: Full path to the written output file.
    
    Notes:
        This function ensures that the output directory exists before writing.
        The JSON file is written with indentation of 2 spaces and UTF-8 encoding.Module template_automation.utils.file_system
============================================
Filesystem-related utilities.

Functions
---------

`ensure_dir_exists(path: Path) ‑> None`
:   Ensure that the given directory exists, creating it along with any
    necessary parent directories if it does not.
    
    Args:
        path (Path): Directory path to ensure exists.
    
    Notes:
        Uses `Path.mkdir` with `parents=True` and `exist_ok=True` to
        create intermediate directories as needed.

`iter_json_files(directory: Path, extension: str = '.json') ‑> Iterable[pathlib.Path]`
:   Recursively iterate over all files with the given extension in the directory.
    
    Args:
        directory (Path): Directory to search for files.
        extension (str, optional): File extension to filter by. Defaults to ".json".
    
    Returns:
        Iterable[Path]: Generator of Path objects matching the extension.
    
    Notes:
        If `directory` is not a valid directory, an empty generator is returned.Module template_automation.utils
================================

Sub-modules
-----------
* template_automation.utils.file_system
* template_automation.utils.logging_utils
* template_automation.utils.validationModule template_automation.utils.logging_utils
==============================================
Centralized logging configuration.

Functions
---------

`setup_logging(level: str = 'INFO') ‑> None`
:   Configure basic logging for the application.
    
    Args:
        level (str, optional): Logging level. One of "DEBUG", "INFO",
            "WARNING", "ERROR", "CRITICAL". Defaults to "INFO".
    
    Notes:
        Uses `logging.basicConfig` to configure the root logger with:
        - Specified logging level.
        - Format: "%(asctime)s [%(levelname)s] %(name)s: %(message)s".
        - Output stream: `sys.stdout`.
        If an invalid level is provided, defaults to INFO.Module template_automation.utils.validation
===========================================
Validation functions for master templates, playbooks, etc.

Functions
---------

`validate_master_template(template: Dict[str, Any]) ‑> None`
:   Validate an Azure Resource Manager (ARM) template.
    
    Args:
        template (Dict[str, Any]): The ARM template JSON as a dictionary.
    
    Raises:
        ValueError: If the template is invalid.
    
    Checks performed:
        - Template is a dictionary.
        - Required top-level fields: "$schema", "contentVersion", "resources".
        - "resources" is a list.
        - Each resource has a "type" and "name".