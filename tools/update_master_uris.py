#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


RE_DEPLOY = re.compile(r"deploy", re.IGNORECASE)  # deploy.json, Deploy_Sophos.json, etc.


def _repo_root() -> Path:
    ws = os.environ.get("GITHUB_WORKSPACE")
    if ws:
        return Path(ws)
    return Path.cwd()


def _raw_uri(owner: str, repo: str, branch: str, rel_path: str) -> str:
    rel_path = rel_path.replace("\\", "/")
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{rel_path}"


def _find_deploy_templates(repo_root: Path) -> List[Path]:
    """
    NUEVA ESTRUCTURA:
      <Integración>/output/deploy.json  (o cualquier *deploy*.json dentro de output)

    Solo consideramos deploys cuya carpeta padre sea exactamente 'output'.
    """
    out: List[Path] = []
    for p in repo_root.rglob("*.json"):
        if not RE_DEPLOY.search(p.name):
            continue
        if p.parent.name != "output":
            continue
        out.append(p)
    return sorted(out)


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _update_deploy_file(
    deploy_path: Path,
    repo_root: Path,
    owner: str,
    repo: str,
    branch: str,
) -> Tuple[bool, List[str]]:
    """
    Actualiza properties.templateLink.uri de cada Microsoft.Resources/deployments
    para que apunte al raw de la rama actual.

    Ahora asume:
      <Entidad>/output/<deploy*.json>
      <Entidad>/output/<playbooks json>
    (y mantiene fallback por compatibilidad)
    """
    data = _load_json(deploy_path)
    resources = data.get("resources", [])
    if not isinstance(resources, list):
        return False, []

    changes: List[str] = []
    changed = False

    # carpeta donde están los playbooks según la nueva estructura
    folder = deploy_path.parent  # .../output
    fallback_folder = folder.parent  # .../<Entidad>

    for r in resources:
        if not isinstance(r, dict):
            continue
        if r.get("type") != "Microsoft.Resources/deployments":
            continue

        name = r.get("name")
        props = r.get("properties")
        if not isinstance(props, dict):
            continue
        tl = props.get("templateLink")
        if not isinstance(tl, dict):
            continue
        if not isinstance(name, str) or not name.strip():
            continue

        # Intentos en orden:
        # 1) output/Cliente_<name>.json
        # 2) output/<name>.json
        # 3) <Entidad>/Cliente_<name>.json   (compat)
        # 4) <Entidad>/<name>.json           (compat)
        candidates = [
            folder / f"Cliente_{name}.json",
            folder / f"{name}.json",
            fallback_folder / f"Cliente_{name}.json",
            fallback_folder / f"{name}.json",
        ]

        target: Path | None = None
        for c in candidates:
            if c.is_file():
                target = c
                break

        if target is None:
            # no tocamos esa uri si no encontramos el JSON objetivo
            continue

        rel = target.resolve().relative_to(repo_root.resolve()).as_posix()
        new_uri = _raw_uri(owner, repo, branch, rel)

        old_uri = tl.get("uri")
        if old_uri != new_uri:
            tl["uri"] = new_uri
            changed = True
            changes.append(f"{deploy_path}: {name} -> {new_uri}")

    if changed:
        _save_json(deploy_path, data)

    return changed, changes


def main() -> int:
    repo_root = _repo_root()

    owner = os.environ.get("GITHUB_OWNER", "").strip()
    repo = os.environ.get("GITHUB_REPO", "").strip()
    branch = os.environ.get("GITHUB_BRANCH", "").strip()

    if not owner or not repo or not branch:
        print("ERROR: faltan env vars. Requiere: GITHUB_OWNER, GITHUB_REPO, GITHUB_BRANCH")
        return 0  # no rompas el workflow

    deploys = _find_deploy_templates(repo_root)
    if not deploys:
        print("No se encontraron deploy templates dentro de carpetas 'output/'.")
        return 0

    any_changed = False
    all_changes: List[str] = []

    for d in deploys:
        changed, changes = _update_deploy_file(d, repo_root, owner, repo, branch)
        if changed:
            any_changed = True
            all_changes.extend(changes)

    if any_changed:
        print("URIs actualizadas:")
        for c in all_changes:
            print(f" - {c}")
    else:
        print("No hubo cambios de URIs.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
