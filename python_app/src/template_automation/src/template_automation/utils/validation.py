"""
Validation functions for master templates, playbooks, etc.

"""

from __future__ import annotations
from typing import Any, Dict, List

def validate_master_template(template: Dict[str, Any]) -> None:
    """
    Validate an Azure Resource Manager (ARM) template.

    Args:
        template (Dict[str, Any]): The ARM template JSON as a dictionary.

    Raises:
        ValueError: If the template is invalid.

    Checks performed:
        - Template is a dictionary.
        - Required top-level fields: "$schema", "contentVersion", "resources".
        - "resources" is a list.
        - Each resource has a "type" and "name".
    """
    if not isinstance(template, dict):
        raise ValueError("ARM template must be a dictionary.")

    # Required top-level fields
    required_fields = ["$schema", "contentVersion", "resources"]
    for field in required_fields:
        if field not in template:
            raise ValueError(f'Missing required top-level field: "{field}".')

    # Validate resources
    resources = template["resources"]
    if not isinstance(resources, list):
        raise ValueError('"resources" must be a list.')

    for i, res in enumerate(resources):
        if not isinstance(res, dict):
            raise ValueError(f'Resource at index {i} must be a dictionary.')
        if "type" not in res:
            raise ValueError(f'Resource at index {i} is missing the "type" field.')
        if "name" not in res:
            raise ValueError(f'Resource at index {i} is missing the "name" field.')

    # Optional: validate parameters or outputs if present
    for section in ["parameters", "outputs"]:
        if section in template:
            if not isinstance(template[section], dict):
                raise ValueError(f'"{section}" section must be a dictionary.')

    # Further checks can be added:
    # - Check for unique resource names
    # - Validate allowed resource types
    # - Validate dependencies
