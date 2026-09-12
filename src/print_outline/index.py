"""Render the auto block for both project and non-project folders.

A single `generate_index` call covers both cases. Non-project folders get a
plain children listing. Project folders additionally get file tables, an
image gallery, sub-project links, and a Spoolman-backed filaments table.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from print_outline.formatting import human_size, iso_date, md_table_row, wikilink_target
from print_outline.frontmatter import read_filaments, read_priority
from print_outline.maintenance import is_maintenance_folder, render_maintenance_tasks
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
        priority = read_priority(folder / index_filename_for(folder, inputs.vault))
        if priority > 0:
            sections.append(f"**Priority:** {priority}")
        sections.extend(_project_sections(inputs))
    else:
        sections.extend(_non_project_sections(inputs))

    return "\n\n".join(s.rstrip() for s in sections if s.strip())


def _child_priority(child: Path, vault: Path, config: Config) -> int:
    if not is_project(child, vault, config):
        return 0
    return read_priority(child / index_filename_for(child, vault))


def _sort_by_priority(children: list[Path], vault: Path, config: Config) -> list[Path]:
    return sorted(children, key=lambda c: (-_child_priority(c, vault, config), c.name))


def _link_with_priority(child: Path, vault: Path, config: Config) -> str:
    target = _child_index_link(child, vault)
    priority = _child_priority(child, vault, config)
    suffix = f" — Priority: {priority}" if priority > 0 else ""
    return f"- [[{target}|{child.name}]]{suffix}"


def _non_project_sections(inputs: IndexInputs) -> Iterable[str]:
    cfg = inputs.config
    children = child_dirs_for_index(inputs.folder, cfg)
    own_index = index_filename_for(inputs.folder, inputs.vault)

    if children:
        ordered = _sort_by_priority(list(children), inputs.vault, cfg)
        lines = ["## Folders"]
        lines.extend(_link_with_priority(child, inputs.vault, cfg) for child in ordered)
        yield "\n".join(lines)

    if is_maintenance_folder(inputs.folder, inputs.vault, cfg):
        # Maintenance folder gets a `## Tasks` snapshot table instead of the
        # generic `## Notes` listing — same task slugs but with schedule
        # metadata and a today-due flag for the maintenance skill.
        yield render_maintenance_tasks(inputs.folder)
        return

    notes = child_notes_for_index(inputs.folder, index_filename=own_index)
    if notes:
        lines = ["## Notes"]
        for note in notes:
            stem = note.stem
            target = wikilink_target(note.with_suffix("").relative_to(inputs.vault))
            lines.append(f"- [[{target}|{stem}]]")
        yield "\n".join(lines)


def _child_index_link(child: Path, vault: Path) -> str:
    rel = child.relative_to(vault)
    child_index_stem = index_filename_for(child, vault).removesuffix(".md")
    return f"{wikilink_target(rel)}/{child_index_stem}"


def _project_sections(inputs: IndexInputs) -> Iterable[str]:
    cfg = inputs.config
    project = inputs.folder
    vault = inputs.vault

    yield from _file_table_section(project, vault, cfg, kind="cad", heading="CAD")
    yield from _file_table_section(project, vault, cfg, kind="stl", heading="STL")
    yield from _file_table_section(
        project, vault, cfg, kind="slice", heading="Slicer (3MF / GCODE)",
    )
    yield from _filaments_section(project, vault, cfg, inputs.spoolman)
    yield from _image_gallery_section(project, vault, cfg)
    yield from _subprojects_section(project, vault, cfg)


def _file_table_section(
    project: Path, vault: Path, cfg: Config, *, kind: str, heading: str,
) -> Iterable[str]:
    subdir = cfg.project_subdirs[kind]
    files = collect_marker_files(project, subdir, cfg.extensions[kind])
    if not files:
        return
    lines = [
        f"## {heading}",
        md_table_row("File", "Size", "Modified"),
        md_table_row("---", "---", "---"),
    ]
    for path in files:
        target = wikilink_target(path.relative_to(vault))
        lines.append(
            md_table_row(
                f"[[{target}|{path.name}]]",
                human_size(path.stat().st_size),
                iso_date(path.stat().st_mtime),
            ),
        )
    yield "\n".join(lines)


def _image_gallery_section(project: Path, vault: Path, cfg: Config) -> Iterable[str]:
    subdir = cfg.project_subdirs["image"]
    files = collect_marker_files(project, subdir, cfg.extensions["image"])
    if not files:
        return
    lines = [
        "## Images",
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">',
    ]
    lines.extend(
        f'<img src="{wikilink_target(path.relative_to(vault))}" style="width:100%;">'
        for path in files
    )
    lines.append("</div>")
    # Graph-edge sidecar: bare wikilinks so Obsidian's graph view picks up the
    # images. Hidden behind <details> so they don't clutter reader mode.
    # Blank lines around the list are required for Obsidian to switch back to
    # markdown parsing inside the HTML block.
    lines.append("")
    lines.append("<details><summary>Image graph links</summary>")
    lines.append("")
    lines.extend(
        f"- [[{wikilink_target(path.relative_to(vault))}]]" for path in files
    )
    lines.append("")
    lines.append("</details>")
    yield "\n".join(lines)


def _subprojects_section(project: Path, vault: Path, cfg: Config) -> Iterable[str]:
    subprojects = child_subprojects(project, vault, cfg)
    if not subprojects:
        return
    ordered = _sort_by_priority(list(subprojects), vault, cfg)
    lines = ["## Sub-projects"]
    lines.extend(_link_with_priority(child, vault, cfg) for child in ordered)
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
        md_table_row("Spool", "Material", "Color", "Vendor"),
        md_table_row("---", "---", "---", "---"),
    ]
    for spool_id, spool in spools:
        if spool is None:
            link = f"[#{spool_id}]({cfg.spoolman_ui_base_url}/spool/show/{spool_id})"
            lines.append(md_table_row(link, "_unreachable_", "", ""))
            continue
        link_text = f"#{spool_id} — {spool.display_name}".rstrip(" —")
        link = f"[{link_text}]({cfg.spoolman_ui_base_url}/spool/show/{spool_id})"
        color_cell = _color_cell(spool.color_hex)
        lines.append(md_table_row(link, spool.material, color_cell, spool.vendor_name))
    yield "\n".join(lines)


def _color_cell(color_hex: str | None) -> str:
    if not color_hex:
        return ""
    hex_value = color_hex.lstrip("#")
    swatch = (
        f'<span style="display:inline-block;width:1em;height:1em;'
        f"background:#{hex_value};border:1px solid #888;border-radius:2px;"
        f'vertical-align:middle;"></span>'
    )
    return f"{swatch} `#{hex_value}`"


def _filament_fallback(ids: list[int]) -> str:
    listed = ", ".join(str(i) for i in ids)
    return f"## Filaments\n\n_(Spoolman unreachable — listed IDs: {listed})_"


def _humanise(name: str) -> str:
    if not name:
        return ""
    cleaned = name.lstrip("_").replace("-", " ").replace("_", " ").strip()
    return cleaned[:1].upper() + cleaned[1:] if cleaned else name
