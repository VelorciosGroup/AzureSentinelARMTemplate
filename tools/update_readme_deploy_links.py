#!/usr/bin/env python3
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Tuple


# Encuentra el fragmento url-encoded: "...%2Frefs%2Fheads%2F<BRANCH>%2F..."
# y captura <BRANCH> para poder sustituirlo.
RE_ENCODED_REFS_HEADS = re.compile(
    r"(%2Frefs%2Fheads%2F)([^%]+)(%2F)",  # prefix, branch, suffix
    flags=re.IGNORECASE,
)


def update_readme_branch(readme_path: Path, branch: str) -> Tuple[bool, int]:
    """
    Sustituye el branch en enlaces 'Deploy to Azure' que incluyan
    raw.githubusercontent.com y refs/heads/<branch> (url-encoded).
    """
    text = readme_path.read_text(encoding="utf-8")
    original = text

    replacements = 0

    def _repl(m: re.Match) -> str:
        nonlocal replacements
        replacements += 1
        return f"{m.group(1)}{branch}{m.group(3)}"

    # Solo tiene sentido tocar README si hay raw.githubusercontent.com dentro
    # (evita cambios accidentales).
    if "raw.githubusercontent.com" in text:
        text = RE_ENCODED_REFS_HEADS.sub(_repl, text)

    changed = text != original
    if changed:
        readme_path.write_text(text, encoding="utf-8")

    return changed, replacements


def main() -> int:
    branch = os.environ.get("GITHUB_BRANCH", "").strip()
    if not branch:
        print("ERROR: falta env var GITHUB_BRANCH")
        return 2

    readme = Path("README.md")
    if not readme.is_file():
        print("No existe README.md en el root.")
        return 0

    changed, n = update_readme_branch(readme, branch)

    if changed:
        print(f"README.md actualizado: {n} reemplazos a rama '{branch}'.")
    else:
        print("README.md: nada que actualizar.")

    return 0  # 👈 SIEMPRE 0


if __name__ == "__main__":
    raise SystemExit(main())
