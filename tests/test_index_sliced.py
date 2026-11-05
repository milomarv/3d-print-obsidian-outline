"""The bambu-hub `sliced/` folder renders its own table and never becomes an index folder."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

from print_outline.cli import main
from print_outline.index import IndexInputs, generate_index
from print_outline.walker import child_subprojects, ensure_marker_subdirs, is_project, walk_vault
from tests.conftest import make_project

if TYPE_CHECKING:
    from pathlib import Path

    from print_outline.config import Config


def _seed_sliced(project: Path, names: list[str]) -> None:
    sliced = project / "sliced"
    sliced.mkdir(parents=True, exist_ok=True)
    for name in names:
        (sliced / name).write_bytes(b"s" * 120)


def _bare_project(vault: Path, name: str) -> Path:
    project = vault / "projects" / name
    project.mkdir()
    return project


def test_sliced_section_lists_hub_files(vault: Path, config: Config) -> None:
    project = make_project(vault / "projects", "holder", slice_files=["plate.3mf"])
    _seed_sliced(project, ["holder.gcode.3mf", "holder.bgcode"])
    body = generate_index(
        IndexInputs(folder=project, vault=vault, config=config, spoolman=None),
    )
    assert "## Sliced (hub)" in body
    assert "| [[projects/holder/sliced/holder.gcode.3mf\\|holder.gcode.3mf]] | 120 B |" in body
    assert "| [[projects/holder/sliced/holder.bgcode\\|holder.bgcode]] | 120 B |" in body


def test_sliced_section_follows_slicer_section(vault: Path, config: Config) -> None:
    project = make_project(vault / "projects", "holder", slice_files=["plate.3mf"])
    _seed_sliced(project, ["holder.gcode.3mf"])
    body = generate_index(
        IndexInputs(folder=project, vault=vault, config=config, spoolman=None),
    )
    assert body.index("## Slicer (3MF / GCODE)") < body.index("## Sliced (hub)")


def test_sliced_section_omitted_when_folder_removed(vault: Path, config: Config) -> None:
    project = make_project(vault / "projects", "holder", slice_files=["plate.3mf"])
    _seed_sliced(project, ["holder.gcode.3mf"])
    shutil.rmtree(project / "sliced")
    body = generate_index(
        IndexInputs(folder=project, vault=vault, config=config, spoolman=None),
    )
    assert "## Sliced (hub)" not in body
    assert "## Slicer (3MF / GCODE)" in body


def test_sliced_only_project_is_recognised(vault: Path, config: Config) -> None:
    project = _bare_project(vault, "holder")
    _seed_sliced(project, ["holder.gcode.3mf"])
    assert is_project(project, vault, config) is True
    classified = {f.path: f.is_project for f in walk_vault(vault, config)}
    assert classified[project] is True
    assert project / "sliced" not in classified


def test_sliced_folder_is_not_listed_as_subproject(vault: Path, config: Config) -> None:
    parent = make_project(vault / "projects", "parent", cad=["a.step"])
    _seed_sliced(parent, ["parent.gcode.3mf"])
    child = make_project(parent, "child", cad=["b.step"])
    assert child_subprojects(parent, vault, config) == [child]
    body = generate_index(
        IndexInputs(folder=parent, vault=vault, config=config, spoolman=None),
    )
    assert "## Sub-projects" in body
    assert "[[projects/parent/child/child|child]]" in body
    assert "projects/parent/sliced" not in body.split("## Sub-projects")[1]


def test_cli_never_writes_index_inside_sliced(vault: Path) -> None:
    project = _bare_project(vault, "holder")
    _seed_sliced(project, ["holder.gcode.3mf"])
    assert main([str(vault), "--no-spoolman"]) == 0
    assert (project / "holder.md").is_file()
    assert sorted(p.name for p in (project / "sliced").iterdir()) == ["holder.gcode.3mf"]


def test_cli_does_not_scaffold_sliced_but_scaffolds_other_subdirs(vault: Path) -> None:
    project = _bare_project(vault, "holder")
    _seed_sliced(project, ["holder.gcode.3mf"])
    assert main([str(vault), "--no-spoolman"]) == 0
    for sub in ("cad", "stl", "3mf", "images"):
        assert (project / sub).is_dir()
    assert not (project / "sliced" / "sliced.md").exists()


def test_ensure_marker_subdirs_skips_sliced(vault: Path, config: Config) -> None:
    folder = _bare_project(vault, "holder")
    created = ensure_marker_subdirs(folder, config)
    assert "sliced" not in created
    assert not (folder / "sliced").exists()
