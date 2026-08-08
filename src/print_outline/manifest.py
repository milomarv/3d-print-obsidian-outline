"""Generate flat priority manifests, one per project state.

For each state in :data:`MANIFEST_STATES` a file
``<project_root>/_priorities-<state>.md`` lists every project carrying that
``state/<value>`` tag, sorted by ``priority`` descending so the skill can answer
"what's highest in <state>" with a single read instead of walking every folder.

Splitting by state keeps the hot ``ongoing`` read small and stable while the
``finished`` archive grows independently. Querying a single state stays a one-file
read; the rare "everything ranked" question reads all three.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from print_outline.formatting import md_table_row, wikilink_target
from print_outline.frontmatter import read_priority, read_state
from print_outline.walker import index_filename_for, walk_vault

if TYPE_CHECKING:
    from pathlib import Path

    from print_outline.config import Config


MANIFEST_STATES = ("ongoing", "idea", "finished")


def manifest_filename(state: str) -> str:
    """File name of the priority manifest for `state`."""
    return f"_priorities-{state}.md"


def manifest_path(vault: Path, config: Config, state: str) -> Path:
    """Path to the manifest file for `state` inside the vault's project root."""
    return vault / config.project_root / manifest_filename(state)


def render_priorities_manifest(vault: Path, config: Config, state: str) -> str:
    """Return the auto-block body for the `state` manifest. Wrap with FenceLayout to write.

    A folder qualifies for the manifest when it carries the target `state/<value>`
    tag AND is either a file-based project (has marker subdirs) or has been given
    an explicit priority (`prio/<N>` with N > 0). The priority signal lets a
    pre-CAD idea rank in the backlog while keeping un-prioritised organisational
    container folders (which the CLI seeds with the default `prio/0`) out.
    """
    rows: list[tuple[int, Path]] = []
    for folder in walk_vault(vault, config):
        index_path = folder.path / index_filename_for(folder.path, vault)
        if read_state(index_path) != state:
            continue
        priority = read_priority(index_path)
        if not folder.is_project and priority <= 0:
            continue
        rows.append((priority, folder.path.relative_to(vault)))

    rows.sort(key=lambda item: (-item[0], item[1].as_posix()))

    lines = [
        f"# Priorities ({state})",
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
