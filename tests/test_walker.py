"""Walker classifies folders correctly across flat and nested layouts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from print_outline.walker import (
    child_subprojects,
    collect_marker_files,
    walk_vault,
)
from tests.conftest import make_project

if TYPE_CHECKING:
    from pathlib import Path

    from print_outline.config import Config


def test_excludes_obsidian_and_git(vault: Path, config: Config) -> None:
    (vault / ".obsidian").mkdir()
    (vault / ".git").mkdir()
    folders = [f.path.name for f in walk_vault(vault, config)]
    assert ".obsidian" not in folders
    assert ".git" not in folders


def test_detects_flat_project(vault: Path, config: Config) -> None:
    project = make_project(vault / "projects", "keychain", cad=["body.step"])
    folders = list(walk_vault(vault, config))
    classified = {f.path: f.is_project for f in folders}
    assert classified[project] is True
    assert classified[vault / "projects"] is False
    assert classified[vault] is False


def test_marker_subdirs_are_not_walked_as_separate_folders(vault: Path, config: Config) -> None:
    project = make_project(vault / "projects", "keychain", cad=["body.step"])
    walked = {f.path for f in walk_vault(vault, config)}
    assert project / "cad" not in walked
    assert project / "stl" not in walked
    assert project / "3mf" not in walked
    assert project / "images" not in walked


def test_nested_project_detection(vault: Path, config: Config) -> None:
    parent = make_project(vault / "projects", "parent", cad=["a.step"])
    child = make_project(parent, "child", cad=["b.step"])
    classifications = {f.path: f.is_project for f in walk_vault(vault, config)}
    assert classifications[parent] is True
    assert classifications[child] is True


def test_collect_marker_files_filters_extensions(vault: Path, config: Config) -> None:
    project = make_project(
        vault / "projects",
        "keychain",
        cad=["body.step", "drawing.txt", "asm.SLDASM"],
    )
    files = collect_marker_files(project, "cad", config.extensions["cad"])
    names = [f.name for f in files]
    assert "body.step" in names
    assert "asm.SLDASM" in names
    assert "drawing.txt" not in names


def test_solidworks_extensions_recognised_as_cad(vault: Path, config: Config) -> None:
    project = make_project(
        vault / "projects",
        "sw-test",
        cad=["part.sldprt", "asm.sldasm", "drw.slddrw", "lib.sldlfp"],
    )
    files = collect_marker_files(project, "cad", config.extensions["cad"])
    assert {f.name for f in files} == {"part.sldprt", "asm.sldasm", "drw.slddrw", "lib.sldlfp"}


def test_child_subprojects_lists_only_projects(vault: Path, config: Config) -> None:
    parent = make_project(vault / "projects", "parent", cad=["a.step"])
    child = make_project(parent, "child", cad=["b.step"])
    (parent / "ideas").mkdir()
    children = child_subprojects(parent, vault, config)
    assert children == [child]


def test_non_project_folder_not_classified(vault: Path, config: Config) -> None:
    (vault / "projects" / "wip").mkdir()
    classifications = {f.path: f.is_project for f in walk_vault(vault, config)}
    assert classifications[vault / "projects" / "wip"] is False
