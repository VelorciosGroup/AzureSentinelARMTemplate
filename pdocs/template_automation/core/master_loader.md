Module template_automation.core.master_loader
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
        validation on the loaded data. Currently, this is a stub for future validation logic.