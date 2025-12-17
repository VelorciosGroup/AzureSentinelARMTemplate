#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


RE_DEPLOY = re.compile(r"deploy", re.IGNORECASE)  # master template contiene "deploy" en el filename


def _repo_root() -> Path:
    # En Actions, el repo se clona en el cwd normalmente. Aun así, soportamos GITHUB_WORKSPACE.
    ws = os.environ.get("GITHUB_WORKSPACE")
    if ws:
        return Path(ws)
    return Path.cwd()


def _raw_uri(owner: str, repo: str, branch: str, rel_path: str) -> str:
    # rel_path debe usar "/" (no backslashes)
    rel_path = rel_path.replace("\\", "/")
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{rel_path}"


def _find_deploy_templates(repo_root: Path) -> List[Path]:
    # Busca *cualquier* json que tenga "deploy" en el nombre (deploy.json, Deploy_Sophos.json, etc.)
    out: List[Path] = []
    for p in repo_root.rglob("*.json"):
        if RE_DEPLOY.search(p.name):
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

    Asume estructura:
      <CarpetaEntidad>/<Deploy*.json>
      <CarpetaEntidad>/<Cliente_*.json> (playbooks)
    """
    data = _load_json(deploy_path)
    resources = data.get("resources", [])
    if not isinstance(resources, list):
        return False, []

    changes: List[str] = []
    changed = False

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

        # Archivo esperado: carpeta del deploy + Cliente_<name>.json
        # (si no existe, intentamos <name>.json)
        folder = deploy_path.parent
        candidate1 = folder / f"Cliente_{name}.json" if isinstance(name, str) else None
        candidate2 = folder / f"{name}.json" if isinstance(name, str) else None

        target: Path | None = None
        if candidate1 and candidate1.is_file():
            target = candidate1
        elif candidate2 and candidate2.is_file():
            target = candidate2
        else:
            # Si no encontramos el playbook, no tocamos esa uri
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
        print("No se encontraron deploy templates (archivos .json que contengan 'deploy' en el nombre).")
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

    return 0  # IMPORTANTÍSIMO: nunca salir con 1 aquí


if __name__ == "__main__":
    raise SystemExit(main())
