import argparse
import json
import sys
from typing import Dict

from .core import replace_literals, add_parameter_definitions


def parse_param_args(param_args):
    params: Dict[str, str] = {}
    for arg in param_args or []:
        if "=" not in arg:
            print(f"[WARN] Ignoring --param '{arg}' (no name=value)", file=sys.stderr)
            continue
        name, value = arg.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name:
            print(f"[WARN] Ignoring --param '{arg}' (empty name)", file=sys.stderr)
            continue
        params[value] = name  # ojo: literal -> nombre_param
    return params


def main():
    parser = argparse.ArgumentParser(
        description="Parametrize ARM template by replacing literals with parameters."
    )
    parser.add_argument("-i", "--input", required=True, help="Input ARM template JSON")
    parser.add_argument("-o", "--output", required=True, help="Output ARM template JSON")
    parser.add_argument(
        "-p",
        "--param",
        action="append",
        help="Parameter definition in the form paramName=literalValue. Can be repeated."
    )
    args = parser.parse_args()

    literal_to_param = parse_param_args(args.param)
    if not literal_to_param:
        print("[ERROR] No parameters provided.", file=sys.stderr)
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as f:
        template = json.load(f)

    new_template = replace_literals(template, literal_to_param)
    add_parameter_definitions(new_template, literal_to_param)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(new_template, f, indent=4, ensure_ascii=False)
        f.write("\n")


if __name__ == "__main__":
    main()
