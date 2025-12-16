Module template_automation.core.writer
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
        The JSON file is written with indentation of 2 spaces and UTF-8 encoding.