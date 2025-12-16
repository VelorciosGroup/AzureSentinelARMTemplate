"""
Módulo de línea de comandos.

Se encarga de:
- Parsear argumentos
- Configurar logging
- Llamar al pipeline principal de procesamiento
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .utils.logging_utils import setup_logging
from .core.transformer import run_automation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="template_automation",
        description=(
            "Herramienta para aplicar una master template sobre "
            "un conjunto de playbooks JSON."
        ),
    )

    parser.add_argument(
        "-master",
        "-m",
        dest="master_path",
        type=Path,
        required=True,
        help="Ruta al fichero JSON de la master template (ej: Deploy_CrowdStrike.json).",
    )

    parser.add_argument(
        "-dirin",
        "-i",
        dest="dir_in",
        type=Path,
        required=True,
        help="Directorio de entrada con los playbooks a procesar.",
    )

    parser.add_argument(
        "-dirout",
        "-o",
        dest="dir_out",
        type=Path,
        required=True,
        help="Directorio de salida para escribir los playbooks transformados.",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Aumenta el nivel de verbosidad (usa -v, -vv, ...).",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Configurar logging según nivel de -v
    if args.verbose >= 2:
        level = "DEBUG"
    elif args.verbose == 1:
        level = "INFO"
    else:
        level = "WARNING"

    setup_logging(level)

    # Ejecutar pipeline principal
    run_automation(
        master_path=args.master_path,
        dir_in=args.dir_in,
        dir_out=args.dir_out,
    )

    return 0
