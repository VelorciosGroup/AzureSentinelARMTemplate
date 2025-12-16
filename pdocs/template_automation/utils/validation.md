Module template_automation.utils.validation
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