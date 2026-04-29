"""Generate a flat priorities manifest for the whole vault.

One file `<project_root>/_priorities.md` lists every project (including nested
sub-projects) sorted by `priority` descending so the skill can answer
"what's highest" with a single read instead of walking every folder.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from print_outline.formatting import md_table_row, wikilink_target
from print_outline.frontmatter import read_priority
from print_outline.walker import index_filename_for, is_project, walk_vault

if TYPE_CHECKING:
    from pathlib import Path

    from print_outline.config import Config


MANIFEST_FILENAME = "_priorities.md"


def manifest_path(vault: Path, config: Config) -> Path:
    """Path to the manifest file inside the vault's project root."""
    return vault / config.project_root / MANIFEST_FILENAME


def render_priorities_manifest(vault: Path, config: Config) -> str:
    """Return the auto-block body for the manifest. Wrap with FenceLayout to write."""
    rows: list[tuple[int, Path]] = []
    for folder in walk_vault(vault, config):
        if not is_project(folder.path, vault, config):
            continue
        priority = read_priority(folder.path / index_filename_for(folder.path, vault))
        rows.append((priority, folder.path.relative_to(vault)))

    rows.sort(key=lambda item: (-item[0], item[1].as_posix()))

    lines = [
        "# Priorities",
        "",
        md_table_row("Priority", "Project"),
        md_table_row("---", "---"),
    ]
    for priority, rel in rows:
        index_stem = index_filename_for(vault / rel, vault).removesuffix(".md")
        target = f"{wikilink_target(rel)}/{index_stem}"
        link = f"[[{target}|{rel.as_posix()}]]"
        lines.append(md_table_row(str(priority), link))
    return "\n".join(lines)
