"""
Funciones de validación (master, playbooks, etc.).
Por ahora son stubs para no frenar el desarrollo.
"""

from __future__ import annotations

from typing import Any, Dict


def validate_master_template(data: Dict[str, Any]) -> None:
    """
    Validación simple de la master template.

    De momento solo comprueba que sea un dict y deja un hook
    para que metas validaciones más estrictas (esquemas, etc.).
    """
    if not isinstance(data, dict):
        raise ValueError("La master template JSON debe ser un objeto (dict).")

    # Aquí podrías validar campos obligatorios, esquemas, etc.
    # TODO: implementar validaciones específicas de Azure/Logic Apps si lo necesitas.

