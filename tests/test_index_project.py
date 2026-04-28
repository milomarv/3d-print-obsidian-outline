"""Project folders render file tables, image gallery, and filament fallback."""

from __future__ import annotations

from typing import TYPE_CHECKING

from print_outline.index import IndexInputs, generate_index
from tests.conftest import make_project

if TYPE_CHECKING:
    from pathlib import Path

    from print_outline.config import Config


def test_cad_table_rendered(vault: Path, config: Config) -> None:
    project = make_project(vault / "projects", "keychain", cad=["body.step", "asm.sldasm"])
    body = generate_index(
        IndexInputs(folder=project, vault=vault, config=config, spoolman=None),
    )
    assert "## CAD" in body
    assert "body.step" in body
    assert "asm.sldasm" in body


def test_stl_and_slice_tables(vault: Path, config: Config) -> None:
    project = make_project(
        vault / "projects",
        "keychain",
        stl=["mesh.stl"],
        slice_files=["plate.3mf", "plate.gcode"],
    )
    body = generate_index(
        IndexInputs(folder=project, vault=vault, config=config, spoolman=None),
    )
    assert "## STL" in body
    assert "mesh.stl" in body
    assert "## Slicer" in body
    assert "plate.3mf" in body


def test_images_gallery_embeds(vault: Path, config: Config) -> None:
    project = make_project(vault / "projects", "keychain", images=["a.jpg", "b.png"])
    body = generate_index(
        IndexInputs(folder=project, vault=vault, config=config, spoolman=None),
    )
    assert "## Images" in body
    assert "![[images/a.jpg]]" in body
    assert "![[images/b.png]]" in body


def test_empty_project_omits_empty_tables(vault: Path, config: Config) -> None:
    project = make_project(vault / "projects", "empty")
    body = generate_index(
        IndexInputs(folder=project, vault=vault, config=config, spoolman=None),
    )
    assert "## CAD" not in body
    assert "## STL" not in body
    assert "## Slicer" not in body
    assert "## Images" not in body
    assert body.startswith("# ")


def test_filament_fallback_when_spoolman_disabled(vault: Path, config: Config) -> None:
    project = make_project(
        vault / "projects",
        "keychain",
        cad=["a.step"],
        notes="---\nfilaments: [12, 34]\n---\n",
    )
    body = generate_index(
        IndexInputs(folder=project, vault=vault, config=config, spoolman=None),
    )
    assert "## Filaments" in body
    assert "Spoolman unreachable" in body
    assert "12, 34" in body


def test_filament_section_skipped_without_frontmatter(vault: Path, config: Config) -> None:
    project = make_project(vault / "projects", "keychain", cad=["a.step"])
    body = generate_index(
        IndexInputs(folder=project, vault=vault, config=config, spoolman=None),
    )
    assert "## Filaments" not in body
