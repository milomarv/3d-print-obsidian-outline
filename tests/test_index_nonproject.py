"""Non-project folders render a children listing only."""

from __future__ import annotations

from typing import TYPE_CHECKING

from print_outline.index import IndexInputs, generate_index
from tests.conftest import make_project

if TYPE_CHECKING:
    from pathlib import Path

    from print_outline.config import Config


def test_root_lists_projects_subfolder(vault: Path, config: Config) -> None:
    make_project(vault / "projects", "keychain", cad=["a.step"])
    body = generate_index(IndexInputs(folder=vault, vault=vault, config=config, spoolman=None))
    assert "## Folders" in body
    assert "[[projects/_index|projects]]" in body


def test_projects_root_lists_children(vault: Path, config: Config) -> None:
    make_project(vault / "projects", "keychain", cad=["a.step"])
    make_project(vault / "projects", "spool-holder", stl=["body.stl"])
    body = generate_index(
        IndexInputs(folder=vault / "projects", vault=vault, config=config, spoolman=None),
    )
    assert "[[keychain/_index|keychain]]" in body
    assert "[[spool-holder/_index|spool-holder]]" in body


def test_non_project_folder_omits_file_tables(vault: Path, config: Config) -> None:
    (vault / "projects" / "wip").mkdir()
    body = generate_index(
        IndexInputs(folder=vault / "projects" / "wip", vault=vault, config=config, spoolman=None),
    )
    assert "## CAD" not in body
    assert "## Filaments" not in body


def test_notes_in_non_project_folder_listed(vault: Path, config: Config) -> None:
    (vault / "projects" / "wip").mkdir()
    (vault / "projects" / "wip" / "ideas.md").write_text("# Ideas\n", encoding="utf-8")
    body = generate_index(
        IndexInputs(folder=vault / "projects" / "wip", vault=vault, config=config, spoolman=None),
    )
    assert "## Notes" in body
    assert "[[ideas|ideas]]" in body
