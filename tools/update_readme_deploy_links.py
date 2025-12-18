#!/usr/bin/env python3
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote


RE_DEPLOY_JSON = re.compile(r"^.*deploy.*\.json$", flags=re.IGNORECASE)
RE_HTML_TABLE = re.compile(r"<table>.*?</table>", flags=re.IGNORECASE | re.DOTALL)

IGNORE_DIRS = {
    ".git",
    ".github",
    "tools",
    "__pycache__",
    "python_app",
}

DISPLAY_NAMES: Dict[str, str] = {
    "Sophos": "Sophos",
    "CrowdStrike": "CrowdStrike",
    "API_parser_usernames": "API Username Parser",
}

PYAPP_BEGIN = "<!-- BEGIN python_app/README.md -->"
PYAPP_END = "<!-- END python_app/README.md -->"


def _is_integration_dir(p: Path) -> bool:
    return (
        p.is_dir()
        and p.name not in IGNORE_DIRS
        and not p.name.startswith(".")
        and (p / "output").is_dir()
    )


def _find_deploy_file(files: List[Path]) -> Optional[Path]:
    for f in files:
        if RE_DEPLOY_JSON.match(f.name):
            return f
    return None


def _sort_files(files: List[Path], deploy: Optional[Path]) -> List[Path]:
    def key(p: Path) -> Tuple[int, str]:
        if deploy and p.name == deploy.name:
            return (2, p.name.lower())
        if p.name.startswith("Cliente_"):
            return (0, p.name.lower())
        return (1, p.name.lower())

    return sorted(files, key=key)


def _raw_github_url(owner: str, repo: str, branch: str, relpath: str) -> str:
    relpath = relpath.replace("\\", "/")
    return f"https://raw.githubusercontent.com/{owner}/{repo}/refs/heads/{branch}/{relpath}"


def _azure_deploy_link(raw_url: str) -> str:
    return f"https://portal.azure.com/#create/Microsoft.Template/uri/{quote(raw_url, safe='')}"


def build_table(owner: str, repo: str, branch: str, root: Path) -> str:
    integration_dirs = sorted(
        [d for d in root.iterdir() if _is_integration_dir(d)],
        key=lambda p: p.name.lower(),
    )

    rows: List[str] = [
        "<table>",
        "  <tr>",
        "    <th>Integración</th>",
        "    <th>Deploy</th>",
        "    <th>Contenido</th>",
        "  </tr>",
        "",
    ]

    for d in integration_dirs:
        output_dir = d / "output"
        json_files = [
            p for p in output_dir.iterdir()
            if p.is_file() and p.suffix.lower() == ".json"
        ]

        if not json_files:
            continue

        deploy = _find_deploy_file(json_files)
        ordered = _sort_files(json_files, deploy)

        display_name = DISPLAY_NAMES.get(d.name, d.name.replace("_", " "))

        if deploy:
            raw_url = _raw_github_url(
                owner, repo, branch, f"{d.name}/output/{deploy.name}"
            )
            deploy_cell = (
                f'      <a href="{_azure_deploy_link(raw_url)}">\n'
                f'        <img src="./Button.png" alt="Deploy to Azure" width="140px" />\n'
                f"      </a>"
            )
        else:
            deploy_cell = "      <i>No deploy.json</i>"

        content_lines = []
        for f in ordered:
            rel = f"./{d.name}/output/{f.name}"
            content_lines.append(f'      • <a href="{rel}">{f.name}</a><br>')

        rows.extend(
            [
                "  <tr>",
                f"    <td><b>{display_name}</b></td>",
                "    <td>",
                deploy_cell,
                "    </td>",
                "    <td>",
                "\n".join(content_lines).rstrip("<br>"),
                "    </td>",
                "  </tr>",
                "",
            ]
        )

    rows.append("</table>")
    return "\n".join(rows) + "\n"


def update_readme(readme_path: Path, new_table: str):
    text = readme_path.read_text(encoding="utf-8")
    original = text

    if RE_HTML_TABLE.search(text):
        text = RE_HTML_TABLE.sub(new_table, text, count=1)
    else:
        text = text.rstrip() + "\n\n" + new_table

    if text != original:
        readme_path.write_text(text, encoding="utf-8")
        print("README.md actualizado")
    else:
        print("README.md sin cambios")


def append_python_app_readme(root_readme: Path, python_app_readme: Path) -> None:
    """
    Appendea el contenido de python_app/README.md al final del README raíz,
    pero sin duplicarlo en ejecuciones sucesivas (usa marcadores BEGIN/END).
    """
    if not root_readme.exists() or not python_app_readme.exists():
        return

    root_text = root_readme.read_text(encoding="utf-8")
    py_text = python_app_readme.read_text(encoding="utf-8").rstrip()

    block = f"{PYAPP_BEGIN}\n\n{py_text}\n\n{PYAPP_END}\n"

    # Si ya existe el bloque, lo reemplazamos (por si cambió python_app/README.md)
    if PYAPP_BEGIN in root_text and PYAPP_END in root_text:
        pattern = re.compile(
            re.escape(PYAPP_BEGIN) + r".*?" + re.escape(PYAPP_END),
            flags=re.DOTALL,
        )
        new_root = pattern.sub(block.rstrip("\n"), root_text).rstrip() + "\n"
    else:
        # Si no existe, lo anexamos al final
        new_root = root_text.rstrip() + "\n\n" + block

    if new_root != root_text:
        root_readme.write_text(new_root, encoding="utf-8")
        print("Append de python_app/README.md aplicado")
    else:
        print("Append de python_app/README.md sin cambios")


def main() -> int:
    branch = os.getenv("GITHUB_BRANCH")
    owner = os.getenv("GITHUB_OWNER")
    repo = os.getenv("GITHUB_REPO")

    if not all([branch, owner, repo]):
        print("ERROR: faltan variables de entorno")
        return 2

    readme = Path("README.md")
    if not readme.exists():
        return 0

    table = build_table(owner, repo, branch, Path("."))
    update_readme(readme, table)

    # ✅ Al final: append del README dentro de python_app
    append_python_app_readme(readme, Path("python_app/README.md"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
