"""Vault traversal and project detection."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from print_outline.config import Config


@dataclass(frozen=True)
class Folder:
    """A single directory inside the vault, classified for downstream rendering."""

    path: Path
    is_project: bool


def is_excluded_dir(name: str, config: Config) -> bool:
    if name in config.exclude_dirs:
        return True
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in config.exclude_globs)


def under_project_root(path: Path, vault: Path, config: Config) -> bool:
    """Return True iff `path` lies inside the configured project root."""
    try:
        rel = path.relative_to(vault)
    except ValueError:
        return False
    parts = rel.parts
    return len(parts) >= 1 and parts[0] == config.project_root


def is_project(path: Path, vault: Path, config: Config) -> bool:
    """Detect a project folder per the rule documented in the README."""
    if path == vault:
        return False
    if not under_project_root(path, vault, config):
        return False
    if path.name == config.project_root:
        return False
    return any((path / sub).is_dir() for sub in config.marker_subdirs)


def is_marker_subdir(path: Path, config: Config) -> bool:
    return path.is_dir() and path.name in config.marker_subdirs


def walk_vault(vault: Path, config: Config) -> Iterator[Folder]:
    """Yield every non-excluded folder in the vault, classified."""
    if not vault.is_dir():
        msg = f"vault path is not a directory: {vault}"
        raise NotADirectoryError(msg)
    yield from _walk(vault, vault, config, inside_project=False)


def _walk(
    current: Path,
    vault: Path,
    config: Config,
    *,
    inside_project: bool,
) -> Iterator[Folder]:
    classified_project = is_project(current, vault, config)
    yield Folder(path=current, is_project=classified_project)

    project_carry = inside_project or classified_project

    for child in sorted(current.iterdir()):
        if not child.is_dir():
            continue
        if is_excluded_dir(child.name, config):
            continue
        if project_carry and is_marker_subdir(child, config):
            continue
        yield from _walk(child, vault, config, inside_project=project_carry)


def collect_marker_files(
    project: Path,
    subdir: str,
    valid_exts: list[str],
) -> list[Path]:
    """Return files inside `<project>/<subdir>` matching any extension."""
    root = project / subdir
    if not root.is_dir():
        return []
    accepted_exts = {f".{ext.lower()}" for ext in valid_exts}
    matches: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in accepted_exts:
            continue
        matches.append(path)
    return matches


def child_subprojects(project: Path, vault: Path, config: Config) -> list[Path]:
    """Return direct child folders of `project` that are themselves projects."""
    return sorted(
        child
        for child in project.iterdir()
        if child.is_dir()
        and not is_excluded_dir(child.name, config)
        and not is_marker_subdir(child, config)
        and is_project(child, vault, config)
    )


def child_dirs_for_index(folder: Path, config: Config) -> list[Path]:
    """Return direct child folders to list in a non-project _index.md."""
    return sorted(
        child
        for child in folder.iterdir()
        if child.is_dir() and not is_excluded_dir(child.name, config)
    )


def child_notes_for_index(folder: Path) -> list[Path]:
    """Return direct child .md files to list in a folder's _index.md."""
    skip = {"_index.md"}
    return sorted(
        child
        for child in folder.iterdir()
        if child.is_file() and child.suffix.lower() == ".md" and child.name not in skip
    )
