Module template_automation.cli
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
        - Executes the main automation pipeline by calling `run_automation`.Module template_automation.config
=================================
General project configuration and constants.

Constants:
- JSON_EXTENSION (str): File extension to process (default: ".json").
- DEFAULT_OUTPUT_DIR_NAME (str): Default subdirectory name for output (default: "out").
- PROJECT_ROOT (Path): Project root directory, assuming a `src/` layout.Module template_automation
==========================

Sub-modules
-----------
* template_automation.cli
* template_automation.config
* template_automation.core
* template_automation.utils