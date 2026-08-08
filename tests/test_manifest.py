"""Per-state priority manifests: state filter, sort order, nesting, file naming."""

from __future__ import annotations

from typing import TYPE_CHECKING

from print_outline.manifest import (
    MANIFEST_STATES,
    manifest_filename,
    manifest_path,
    render_priorities_manifest,
)
from tests.conftest import make_project

if TYPE_CHECKING:
    from pathlib import Path

    from print_outline.config import Config


def _state(prio: int, state: str) -> str:
    return f"---\ntags: [prio/{prio}, state/{state}]\n---\n"


def _ongoing(prio: int) -> str:
    return _state(prio, "ongoing")


def test_manifest_sorts_by_priority_desc(vault: Path, config: Config) -> None:
    make_project(vault / "projects", "low", cad=["a.step"], notes=_ongoing(1))
    make_project(vault / "projects", "high", cad=["b.step"], notes=_ongoing(9))
    make_project(vault / "projects", "mid", cad=["c.step"], notes=_ongoing(5))
    body = render_priorities_manifest(vault, config, "ongoing")
    assert body.index("high") < body.index("mid") < body.index("low")


def test_manifest_includes_explicit_priority_zero(vault: Path, config: Config) -> None:
    make_project(vault / "projects", "unset", cad=["a.step"], notes=_ongoing(0))
    body = render_priorities_manifest(vault, config, "ongoing")
    assert "unset" in body
    assert "| 0 |" in body


def test_ongoing_manifest_excludes_idea_state(vault: Path, config: Config) -> None:
    make_project(vault / "projects", "thinking", cad=["a.step"], notes=_state(9, "idea"))
    body = render_priorities_manifest(vault, config, "ongoing")
    assert "thinking" not in body


def test_ongoing_manifest_excludes_finished_state(vault: Path, config: Config) -> None:
    make_project(vault / "projects", "shipped", cad=["a.step"], notes=_state(9, "finished"))
    body = render_priorities_manifest(vault, config, "ongoing")
    assert "shipped" not in body


def test_idea_manifest_includes_idea_and_excludes_others(vault: Path, config: Config) -> None:
    make_project(vault / "projects", "thinking", cad=["a.step"], notes=_state(7, "idea"))
    make_project(vault / "projects", "active", cad=["b.step"], notes=_ongoing(9))
    body = render_priorities_manifest(vault, config, "idea")
    assert "thinking" in body
    assert "active" not in body
    assert body.startswith("# Priorities (idea)")


def test_finished_manifest_includes_finished(vault: Path, config: Config) -> None:
    make_project(vault / "projects", "shipped", cad=["a.step"], notes=_state(4, "finished"))
    body = render_priorities_manifest(vault, config, "finished")
    assert "shipped" in body
    assert "| 4 |" in body
    assert body.startswith("# Priorities (finished)")


def test_prioritized_fileless_folder_is_listed(vault: Path, config: Config) -> None:
    # A folder with no marker subdirs but an explicit prio>0 still ranks (pre-CAD idea).
    concept = vault / "projects" / "concept"
    concept.mkdir()
    (concept / "concept.md").write_text(_state(5, "idea"), encoding="utf-8")
    body = render_priorities_manifest(vault, config, "idea")
    assert "concept" in body
    assert "| 5 |" in body


def test_unprioritized_fileless_folder_is_excluded(vault: Path, config: Config) -> None:
    # A file-less container at the default prio/0 is organisational noise — kept out.
    container = vault / "projects" / "grouping"
    container.mkdir()
    (container / "grouping.md").write_text(_state(0, "idea"), encoding="utf-8")
    body = render_priorities_manifest(vault, config, "idea")
    assert "grouping" not in body


def test_folder_without_state_tag_defaults_to_idea(vault: Path, config: Config) -> None:
    # read_state() defaults a missing state/* tag to "idea", so an un-tagged
    # project surfaces in the idea backlog — never in ongoing or finished.
    make_project(vault / "projects", "no-frontmatter", cad=["a.step"])
    assert "no-frontmatter" not in render_priorities_manifest(vault, config, "ongoing")
    assert "no-frontmatter" not in render_priorities_manifest(vault, config, "finished")
    assert "no-frontmatter" in render_priorities_manifest(vault, config, "idea")


def test_manifest_includes_nested_subprojects(vault: Path, config: Config) -> None:
    parent = make_project(vault / "projects", "parent", cad=["p.step"], notes=_ongoing(2))
    make_project(parent, "child", cad=["c.step"], notes=_ongoing(8))
    body = render_priorities_manifest(vault, config, "ongoing")
    assert "parent/child" in body
    # child priority 8 > parent priority 2 → child appears first
    assert body.index("| 8 |") < body.index("| 2 |")


def test_manifest_link_format(vault: Path, config: Config) -> None:
    make_project(vault / "projects", "keychain", cad=["a.step"], notes=_ongoing(3))
    body = render_priorities_manifest(vault, config, "ongoing")
    assert r"[[projects/keychain/keychain\|projects/keychain]]" in body
    assert "| 3 |" in body


def test_manifest_path_lives_under_project_root(vault: Path, config: Config) -> None:
    for state in MANIFEST_STATES:
        assert manifest_path(vault, config, state) == (
            vault / "projects" / f"_priorities-{state}.md"
        )


def test_manifest_filename_per_state() -> None:
    assert manifest_filename("ongoing") == "_priorities-ongoing.md"
    assert manifest_filename("idea") == "_priorities-idea.md"
    assert manifest_filename("finished") == "_priorities-finished.md"


def test_manifest_header_and_table_present(vault: Path, config: Config) -> None:
    body = render_priorities_manifest(vault, config, "ongoing")
    assert body.startswith("# Priorities (ongoing)")
    assert "| Priority | Project |" in body
