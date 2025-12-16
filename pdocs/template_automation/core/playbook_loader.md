Module template_automation.core.playbook_loader
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
        json.JSONDecodeError: If the file contains invalid JSON.