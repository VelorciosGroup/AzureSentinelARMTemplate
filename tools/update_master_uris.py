#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


DEPLOY_REGEX = re.compile(r"deploy", re.IGNORECASE)


def is_master_template(path: Path) -> bool:
    """
    Devuelve True si el fichero es una master template.
    Criterio: el nombre contiene la palabra 'deploy' (case-insensitive)
    """
    return (
        path.is_file()
        and path.suffix.lower() == ".json"
        and DEPLOY_REGEX.search(path.name) is not None
    )


def update_master_template(
    deploy_path: Path,
    owner: str,
    repo: str,
    branch: str,
) -> Tuple[bool, List[str]]:
    """
    Actualiza templateLink.uri en:
      resources[*] donde type == Microsoft.Resources/deployments

    URI final:
      https://raw.githubusercontent.com/<owner>/<repo>/<branch>/<folder>/Cliente_<deploymentName>.json
    """
    changed = False
    changes_log: List[str] = []

    data: Dict[str, Any] = json.loads(deploy_path.read_text(encoding="utf-8"))
    resources = data.get("resources", [])
    if not isinstance(resources, list):
        return False, changes_log

    folder_posix = deploy_path.parent.as_posix()

    for res in resources:
        if not isinstance(res, dict):
            continue
        if res.get("type") != "Microsoft.Resources/deployments":
            continue

        deployment_name = res.get("name")
        if not isinstance(deployment_name, str) or not deployment_name:
            continue

        props = res.get("properties")
        if not isinstance(props, dict):
            continue

        template_link = props.get("templateLink")
        if not isinstance(template_link, dict):
            continue

        expected_path = f"{folder_posix}/Cliente_{deployment_name}.json"
        expected_uri = (
            f"https://raw.githubusercontent.com/"
            f"{owner}/{repo}/{branch}/{expected_path}"
        )

        current_uri = template_link.get("uri")
        if current_uri != expected_uri:
            template_link["uri"] = expected_uri
            changed = True
            changes_log.append(
                f"{deploy_path.as_posix()}: {deployment_name} -> {expected_uri}"
            )

    if changed:
        deploy_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    return changed, changes_log


def main() -> int:
    owner = os.environ.get("GITHUB_OWNER", "").strip()
    repo = os.environ.get("GITHUB_REPO", "").strip()
    branch = os.environ.get("GITHUB_BRANCH", "").strip()

    if not owner or not repo or not branch:
        print("ERROR: faltan env vars GITHUB_OWNER / GITHUB_REPO / GITHUB_BRANCH")
        return 2

    root = Path(".").resolve()

    master_templates = [
        p for p in root.rglob("*.json") if is_master_template(p)
    ]

    if not master_templates:
        print("No se encontraron master templates (regex: /deploy/i).")
        return 0

    any_changed = False
    all_logs: List[str] = []

    for deploy_path in sorted(master_templates):
        changed, logs = update_master_template(
            deploy_path, owner, repo, branch
        )
        if changed:
            any_changed = True
            all_logs.extend(logs)

    if any_changed:
        print("URIs actualizadas:")
        for line in all_logs:
            print(" -", line)
        return 1

    print("Nada que actualizar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
