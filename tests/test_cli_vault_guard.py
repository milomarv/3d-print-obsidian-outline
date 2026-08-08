"""CLI guard: refuse a vault root that lacks the `project_root/` directory.

Pointing `outline` at a parent dir (e.g. the whole Obsidian vault instead of the
`3d-print/` subfolder) used to silently walk unrelated folders and write a stray
manifest. The guard turns that footgun into a loud error.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from print_outline.cli import _vault_root_error, main
from print_outline.config import resolve_config

if TYPE_CHECKING:
    from pathlib import Path

    from print_outline.config import Config

EXIT_USAGE = 2


def test_valid_vault_root_passes(vault: Path, config: Config) -> None:
    assert _vault_root_error(vault, config) is None


def test_parent_dir_names_the_intended_subfolder(tmp_path: Path) -> None:
    """A parent holding `3d-print/projects/` should point the user at `3d-print/`."""
    sub = tmp_path / "3d-print"
    (sub / "projects").mkdir(parents=True)
    config = resolve_config(sub, explicit=None)

    msg = _vault_root_error(tmp_path, config)
    assert msg is not None
    assert str(sub) in msg
    assert "did you mean" in msg


def test_dir_without_projects_anywhere_is_refused(tmp_path: Path) -> None:
    config = resolve_config(tmp_path, explicit=None)

    msg = _vault_root_error(tmp_path, config)
    assert msg is not None
    assert "refusing to run" in msg


def test_main_exits_with_usage_code_and_writes_nothing_for_wrong_root(tmp_path: Path) -> None:
    """End-to-end: wrong root -> usage exit code, no stray manifest created."""
    (tmp_path / "3d-print" / "projects").mkdir(parents=True)

    rc = main([str(tmp_path)])

    assert rc == EXIT_USAGE
    assert not (tmp_path / "projects").exists()
    assert not (tmp_path / "projects" / "_priorities-ongoing.md").exists()
