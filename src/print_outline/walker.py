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


def ensure_marker_subdirs(folder: Path, config: Config) -> list[str]:
    """Create any missing marker subdirs (`cad/`, `stl/`, `3mf/`, `images/`) in `folder`.

    Returns the names actually created; idempotent — existing subdirs are left
    untouched. Lets the CLI scaffold a project folder so the user can drop files
    straight into a synced `images/` (or CAD/STL/3MF) instead of the folder being
    missing first. Syncthing propagates the empty dirs to every device.
    """
    created: list[str] = []
    for sub in config.marker_subdirs:
        target = folder / sub
        if not target.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            created.append(sub)
    return created


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


def child_notes_for_index(folder: Path, *, index_filename: str) -> list[Path]:
    """Return direct child .md files to list in a folder's index, skipping the index itself.

    Also skips the auto-generated `_priorities-<state>.md` manifests (matched by
    the `_priorities` prefix, so the legacy single-file name is skipped too);
    they would otherwise appear under "Notes" in the projects folder index.
    """
    skip = {index_filename, "_index.md"}
    return sorted(
        child
        for child in folder.iterdir()
        if child.is_file()
        and child.suffix.lower() == ".md"
        and child.name not in skip
        and not child.name.startswith("_priorities")
    )


def index_filename_for(folder: Path, vault: Path) -> str:
    """Return the filename of the auto-generated index for `folder`.

    Folder-note convention: a folder's index is named after the folder
    (e.g. `projects/` → `projects.md`). The vault root uses its own
    directory basename so the rule applies uniformly.
    """
    name = folder.name if folder != vault else vault.name
    return f"{name}.md"
