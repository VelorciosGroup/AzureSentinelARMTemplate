Module template_automation.core.transformer
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
: