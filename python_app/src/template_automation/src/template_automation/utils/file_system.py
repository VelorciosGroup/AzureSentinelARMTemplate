"""
Filesystem-related utilities.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable


def ensure_dir_exists(path: Path) -> None:
    """
    Ensure that the given directory exists, creating it along with any
    necessary parent directories if it does not.

    Args:
        path (Path): Directory path to ensure exists.

    Notes:
        Uses `Path.mkdir` with `parents=True` and `exist_ok=True` to
        create intermediate directories as needed.
    """
    path.mkdir(parents=True, exist_ok=True)


def iter_json_files(directory: Path, extension: str = ".json") -> Iterable[Path]:
    """
    Recursively iterate over all files with the given extension in the directory.

    Args:
        directory (Path): Directory to search for files.
        extension (str, optional): File extension to filter by. Defaults to ".json".

    Returns:
        Iterable[Path]: Generator of Path objects matching the extension.

    Notes:
        If `directory` is not a valid directory, an empty generator is returned.
    """
    if not directory.is_dir():
        return []

    yield from directory.rglob(f"*{extension}")
