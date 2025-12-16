Module template_automation.utils.logging_utils
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
        If an invalid level is provided, defaults to INFO.