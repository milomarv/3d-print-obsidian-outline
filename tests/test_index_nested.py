"""Nested-project boundary rule: parent's tables don't include child's files."""

from __future__ import annotations

from typing import TYPE_CHECKING

from print_outline.index import IndexInputs, generate_index
from tests.conftest import make_project

if TYPE_CHECKING:
    from pathlib import Path

    from print_outline.config import Config


def test_parent_lists_child_under_subprojects(vault: Path, config: Config) -> None:
    parent = make_project(vault / "projects", "parent", cad=["parent.step"])
    make_project(parent, "child", cad=["child.step"])
    body = generate_index(IndexInputs(folder=parent, vault=vault, config=config, spoolman=None))
    assert "## Sub-projects" in body
    assert "[[child/_index|child]]" in body


def test_parent_tables_exclude_childs_files(vault: Path, config: Config) -> None:
    parent = make_project(vault / "projects", "parent", cad=["parent.step"])
    make_project(parent, "child", cad=["child.step"])
    body = generate_index(IndexInputs(folder=parent, vault=vault, config=config, spoolman=None))
    assert "parent.step" in body
    assert "child.step" not in body


def test_child_renders_independent_index(vault: Path, config: Config) -> None:
    parent = make_project(vault / "projects", "parent", cad=["parent.step"])
    child = make_project(parent, "child", cad=["child.step"])
    body = generate_index(IndexInputs(folder=child, vault=vault, config=config, spoolman=None))
    assert "child.step" in body
    assert "parent.step" not in body
