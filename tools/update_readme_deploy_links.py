#!/usr/bin/env python3
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote


# Detecta deploys tipo "Deploy_Sophos.json", "deploy.json", "DEPLOY_whatever.json", etc.
RE_DEPLOY_JSON = re.compile(r"^.*deploy.*\.json$", flags=re.IGNORECASE)

# Captura el primer <table>...</table> para reemplazarlo entero
RE_HTML_TABLE = re.compile(r"<table>.*?</table>", flags=re.IGNORECASE | re.DOTALL)


# Carpetas a ignorar como integraciones
IGNORE_DIRS = {
    ".git",
    ".github",
    "tools",
    "__pycache__",
}

# Nombres bonitos para mostrar en README
DISPLAY_NAMES: Dict[str, str] = {
    "Sophos": "Sophos",
    "CrowdStrike": "CrowdStrike",
    "API_parser_usernames": "API Username Parser",
}


def _is_integration_dir(p: Path) -> bool:
    return p.is_dir() and p.name not in IGNORE_DIRS and not p.name.startswith(".")


def _find_deploy_file(files: List[Path]) -> Optional[Path]:
    for f in files:
        if RE_DEPLOY_JSON.match(f.name):
            return f
    return None


def _sort_files(files: List[Path], deploy: Optional[Path]) -> List[Path]:
    """
    Orden:
      1) Cliente_*.json
      2) resto .json
      3) deploy (al final) si existe
    """
    def key(p: Path) -> Tuple[int, str]:
        name = p.name
        if deploy is not None and p.name == deploy.name:
            return (2, name.lower())
        if name.startswith("Cliente_"):
            return (0, name.lower())
        return (1, name.lower())

    return sorted(files, key=key)


def _raw_github_url(owner: str, repo: str, branch: str, relpath: str) -> str:
    # relpath debe ir con "/" (no backslashes)
    relpath = relpath.replace("\\", "/")
    return f"https://raw.githubusercontent.com/{owner}/{repo}/refs/heads/{branch}/{relpath}"


def _azure_deploy_link(raw_url: str) -> str:
    # Azure portal quiere la URL del template en el parámetro `uri` URL-encoded
    encoded = quote(raw_url, safe="")
    return f"https://portal.azure.com/#create/Microsoft.Template/uri/{encoded}"


def build_table(owner: str, repo: str, branch: str, root: Path) -> str:
    """
    Construye la tabla HTML completa en base al filesystem real.
    """
    integration_dirs = sorted([d for d in root.iterdir() if _is_integration_dir(d)], key=lambda p: p.name.lower())

    rows: List[str] = []
    rows.append("<table>")
    rows.append("  <tr>")
    rows.append("    <th>Integración</th>")
    rows.append("    <th>Deploy</th>")
    rows.append("    <th>Contenido</th>")
    rows.append("  </tr>")
    rows.append("")

    for d in integration_dirs:
        json_files = sorted([p for p in d.iterdir() if p.is_file() and p.suffix.lower() == ".json"], key=lambda p: p.name.lower())
        if not json_files:
            # si no hay json, no lo mostramos (o podrías mostrarlo vacío)
            continue

        deploy = _find_deploy_file(json_files)
        ordered = _sort_files(json_files, deploy)

        display_name = DISPLAY_NAMES.get(d.name, d.name.replace("_", " ").strip())

        # Deploy button: solo si existe deploy
        if deploy is not None:
            raw_url = _raw_github_url(owner, repo, branch, f"{d.name}/{deploy.name}")
            deploy_href = _azure_deploy_link(raw_url)
            deploy_cell = (
                f'      <a href="{deploy_href}">\n'
                f'        <img src="./Button.png" alt="Deploy to Azure" width="140px" />\n'
                f"      </a>"
            )
        else:
            deploy_cell = "      <i>No deploy.json</i>"

        # Contenido: lista de links relativos
        content_lines: List[str] = []
        for f in ordered:
            rel = f"./{d.name}/{f.name}"
            content_lines.append(f'      • <a href="{rel}">{f.name}</a><br>')

        content_cell = "\n".join(content_lines).rstrip("<br>")

        rows.append("  <tr>")
        rows.append(f"    <td><b>{display_name}</b></td>")
        rows.append("    <td>")
        rows.append(deploy_cell)
        rows.append("    </td>")
        rows.append("    <td>")
        rows.append(content_cell)
        rows.append("    </td>")
        rows.append("  </tr>")
        rows.append("")

    rows.append("</table>")
    return "\n".join(rows) + "\n"


def update_readme(readme_path: Path, new_table: str) -> Tuple[bool, int]:
    """
    Reemplaza el primer <table>...</table> por la tabla generada.
    Si no hay tabla, la añade al final.
    """
    text = readme_path.read_text(encoding="utf-8")
    original = text

    replacements = 0
    if RE_HTML_TABLE.search(text):
        text, replacements = RE_HTML_TABLE.subn(new_table, text, count=1)
    else:
        # si no existe tabla, añadimos al final
        text = text.rstrip() + "\n\n" + new_table
        replacements = 1

    changed = (text != original)
    if changed:
        readme_path.write_text(text, encoding="utf-8")

    return changed, replacements


def main() -> int:
    branch = os.environ.get("GITHUB_BRANCH", "").strip()
    if not branch:
        print("ERROR: falta env var GITHUB_BRANCH")
        return 2

    owner = os.environ.get("GITHUB_OWNER", "").strip()
    repo = os.environ.get("GITHUB_REPO", "").strip()
    if not owner or not repo:
        print("ERROR: faltan env vars GITHUB_OWNER / GITHUB_REPO")
        return 2

    root = Path(".")
    readme = root / "README.md"
    if not readme.is_file():
        print("No existe README.md en el root.")
        return 0

    new_table = build_table(owner=owner, repo=repo, branch=branch, root=root)

    changed, n = update_readme(readme, new_table)
    if changed:
        print(f"README.md actualizado: tabla regenerada (reemplazos={n}) para rama '{branch}'.")
    else:
        print("README.md: nada que actualizar.")

    return 0  # ✅ Siempre 0 (Actions nunca debe fallar por 'hubo cambios')


if __name__ == "__main__":
    raise SystemExit(main())
