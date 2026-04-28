"""Render the auto block for both project and non-project folders.

A single `generate_index` call covers both cases. Non-project folders get a
plain children listing. Project folders additionally get file tables, an
image gallery, sub-project links, and a Spoolman-backed filaments table.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from print_outline.formatting import human_size, iso_date, md_table_row, wikilink_target
from print_outline.frontmatter import read_filaments
from print_outline.walker import (
    child_dirs_for_index,
    child_notes_for_index,
    child_subprojects,
    collect_marker_files,
    index_filename_for,
    is_project,
)

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from print_outline.config import Config
    from print_outline.spoolman import Spool, SpoolmanClient


@dataclass(frozen=True)
class IndexInputs:
    folder: Path
    vault: Path
    config: Config
    spoolman: SpoolmanClient | None


def generate_index(inputs: IndexInputs) -> str:
    """Return the markdown body that goes between the AUTO fences."""
    folder = inputs.folder
    title = _humanise(folder.name) if folder != inputs.vault else _humanise(folder.name) or "Vault"
    sections: list[str] = [f"# {title}"]

    if is_project(folder, inputs.vault, inputs.config):
        sections.extend(_project_sections(inputs))
    else:
        sections.extend(_non_project_sections(inputs))

    return "\n\n".join(s.rstrip() for s in sections if s.strip())


def _non_project_sections(inputs: IndexInputs) -> Iterable[str]:
    cfg = inputs.config
    children = child_dirs_for_index(inputs.folder, cfg)
    own_index = index_filename_for(inputs.folder, inputs.vault)
    notes = child_notes_for_index(inputs.folder, index_filename=own_index)

    if children:
        lines = ["## Folders", ""]
        lines.extend(
            f"- [[{_child_index_link(inputs.folder, child, inputs.vault)}|{child.name}]]"
            for child in children
        )
        yield "\n".join(lines)

    if notes:
        lines = ["## Notes", ""]
        for note in notes:
            stem = note.stem
            target = wikilink_target(_rel(inputs.folder, note.with_suffix("")))
            lines.append(f"- [[{target}|{stem}]]")
        yield "\n".join(lines)


def _child_index_link(parent: Path, child: Path, vault: Path) -> str:
    rel = _rel(parent, child)
    child_index_stem = index_filename_for(child, vault).removesuffix(".md")
    return f"{wikilink_target(rel)}/{child_index_stem}"


def _project_sections(inputs: IndexInputs) -> Iterable[str]:
    cfg = inputs.config
    project = inputs.folder

    yield from _file_table_section(project, cfg, kind="cad", heading="CAD")
    yield from _file_table_section(project, cfg, kind="stl", heading="STL")
    yield from _file_table_section(project, cfg, kind="slice", heading="Slicer (3MF / GCODE)")
    yield from _image_gallery_section(project, cfg)
    yield from _subprojects_section(project, inputs.vault, cfg)
    yield from _filaments_section(project, inputs.vault, cfg, inputs.spoolman)


def _file_table_section(project: Path, cfg: Config, *, kind: str, heading: str) -> Iterable[str]:
    subdir = cfg.project_subdirs[kind]
    files = collect_marker_files(project, subdir, cfg.extensions[kind])
    if not files:
        return
    lines = [
        f"## {heading}",
        "",
        md_table_row("File", "Size", "Modified"),
        md_table_row("---", "---", "---"),
    ]
    for path in files:
        rel = _rel(project, path)
        target = wikilink_target(rel)
        lines.append(
            md_table_row(
                f"[[{target}|{path.name}]]",
                human_size(path.stat().st_size),
                iso_date(path.stat().st_mtime),
            ),
        )
    yield "\n".join(lines)


def _image_gallery_section(project: Path, cfg: Config) -> Iterable[str]:
    subdir = cfg.project_subdirs["image"]
    files = collect_marker_files(project, subdir, cfg.extensions["image"])
    if not files:
        return
    lines = ["## Images", ""]
    for path in files:
        rel = _rel(project, path)
        lines.append(f"![[{wikilink_target(rel)}]]")
    yield "\n".join(lines)


def _subprojects_section(project: Path, vault: Path, cfg: Config) -> Iterable[str]:
    subprojects = child_subprojects(project, vault, cfg)
    if not subprojects:
        return
    lines = ["## Sub-projects", ""]
    lines.extend(
        f"- [[{_child_index_link(project, child, vault)}|{child.name}]]"
        for child in subprojects
    )
    yield "\n".join(lines)


def _filaments_section(
    project: Path,
    vault: Path,
    cfg: Config,
    client: SpoolmanClient | None,
) -> Iterable[str]:
    index_path = project / index_filename_for(project, vault)
    ids = read_filaments(index_path)
    if not ids:
        return
    if client is None or not cfg.spoolman_enabled:
        yield _filament_fallback(ids)
        return
    spools: list[tuple[int, Spool | None]] = [
        (spool_id, client.fetch(spool_id)) for spool_id in ids
    ]
    if all(spool is None for _, spool in spools):
        yield _filament_fallback(ids)
        return
    lines = [
        "## Filaments",
        "",
        md_table_row("Spool", "Material", "Color", "Vendor"),
        md_table_row("---", "---", "---", "---"),
    ]
    for spool_id, spool in spools:
        if spool is None:
            link = f"[#{spool_id}]({cfg.spoolman_ui_base_url}/spool/{spool_id})"
            lines.append(md_table_row(link, "_unreachable_", "", ""))
            continue
        link_text = f"#{spool_id} — {spool.display_name}".rstrip(" —")
        link = f"[{link_text}]({cfg.spoolman_ui_base_url}/spool/{spool_id})"
        color_cell = f"`{spool.color_hex}`" if spool.color_hex else ""
        lines.append(md_table_row(link, spool.material, color_cell, spool.vendor_name))
    yield "\n".join(lines)


def _filament_fallback(ids: list[int]) -> str:
    listed = ", ".join(str(i) for i in ids)
    return f"## Filaments\n\n_(Spoolman unreachable — listed IDs: {listed})_"


def _rel(base: Path, target: Path) -> Path:
    return target.relative_to(base)


def _humanise(name: str) -> str:
    if not name:
        return ""
    cleaned = name.lstrip("_").replace("-", " ").replace("_", " ").strip()
    return cleaned[:1].upper() + cleaned[1:] if cleaned else name
