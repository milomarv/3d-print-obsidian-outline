"""The CLI scaffolds marker subdirs for projects and prioritised folders.

So the user can drop files straight into a synced `images/` (or CAD/STL/3MF)
without the folder being missing first — without turning un-prioritised
container folders into projects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from print_outline.cli import main
from print_outline.walker import ensure_marker_subdirs

if TYPE_CHECKING:
    from pathlib import Path

    from print_outline.config import Config

MARKER_SUBDIRS = ("cad", "stl", "3mf", "images")


def _folder_with_tags(parent: Path, name: str, tags: str) -> Path:
    folder = parent / name
    folder.mkdir(parents=True)
    (folder / f"{name}.md").write_text(f"---\ntags: [{tags}]\n---\n", encoding="utf-8")
    return folder


def test_ensure_marker_subdirs_creates_missing_then_is_idempotent(
    tmp_path: Path,
    config: Config,
) -> None:
    folder = tmp_path / "p"
    folder.mkdir()
    created = ensure_marker_subdirs(folder, config)
    assert sorted(created) == sorted(MARKER_SUBDIRS)
    for sub in MARKER_SUBDIRS:
        assert (folder / sub).is_dir()
    assert ensure_marker_subdirs(folder, config) == []


def test_main_scaffolds_prioritised_fileless_folder(vault: Path) -> None:
    idea = _folder_with_tags(vault / "projects", "concept", "prio/5, state/idea")
    assert main([str(vault), "--no-spoolman"]) == 0
    for sub in MARKER_SUBDIRS:
        assert (idea / sub).is_dir()


def test_main_does_not_scaffold_unprioritised_container(vault: Path) -> None:
    container = _folder_with_tags(vault / "projects", "grouping", "prio/0, state/idea")
    assert main([str(vault), "--no-spoolman"]) == 0
    for sub in MARKER_SUBDIRS:
        assert not (container / sub).exists()


def test_main_does_not_scaffold_parent_of_subprojects(vault: Path) -> None:
    # A prioritised grouping that holds child builds is a parent folder; the
    # marker subdirs belong on the leaf builds, not the grouping itself.
    parent = _folder_with_tags(vault / "projects", "grouping", "prio/5, state/idea")
    child = _folder_with_tags(parent, "build", "prio/5, state/idea")
    assert main([str(vault), "--no-spoolman"]) == 0
    for sub in MARKER_SUBDIRS:
        assert not (parent / sub).exists()
        assert (child / sub).is_dir()


def test_main_fills_missing_subdirs_for_existing_project(vault: Path) -> None:
    proj = vault / "projects" / "halfbuilt"
    (proj / "cad").mkdir(parents=True)
    (proj / "cad" / "x.step").write_bytes(b"x")
    assert main([str(vault), "--no-spoolman"]) == 0
    for sub in MARKER_SUBDIRS:
        assert (proj / sub).is_dir()


def test_main_dry_run_scaffolds_nothing(vault: Path) -> None:
    idea = _folder_with_tags(vault / "projects", "concept", "prio/5, state/idea")
    assert main([str(vault), "--no-spoolman", "--dry-run"]) == 0
    for sub in MARKER_SUBDIRS:
        assert not (idea / sub).exists()
