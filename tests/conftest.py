"""Shared fixtures: build fake vaults under tmp_path."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pytest

from print_outline.config import resolve_config

if TYPE_CHECKING:
    from pathlib import Path

    from print_outline.config import Config


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    """Empty vault root with a `.stignore` and an empty `projects/`."""
    (tmp_path / "projects").mkdir()
    (tmp_path / ".stignore").write_text(".obsidian\n.trash\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def config(vault: Path) -> Config:
    return resolve_config(vault, explicit=None)


@dataclass(frozen=True)
class ProjectSpec:
    """Files to seed inside a project's marker subdirs."""

    cad: list[str] = field(default_factory=list)
    stl: list[str] = field(default_factory=list)
    slice_files: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    notes: str | None = None


def make_project(parent: Path, name: str, **kwargs: object) -> Path:
    """Create a project folder with marker subdirs and seed files.

    Keyword args (all optional): cad, stl, slice_files, images (lists of
    filenames), notes (markdown body).
    """
    spec = ProjectSpec(
        cad=_kwarg_list(kwargs, "cad"),
        stl=_kwarg_list(kwargs, "stl"),
        slice_files=_kwarg_list(kwargs, "slice_files"),
        images=_kwarg_list(kwargs, "images"),
        notes=_kwarg_str(kwargs, "notes"),
    )
    project = parent / name
    for sub in ("cad", "stl", "3mf", "images"):
        (project / sub).mkdir(parents=True)
    _seed_files(project / "cad", spec.cad, payload=b"x" * 100)
    _seed_files(project / "stl", spec.stl, payload=b"y" * 200)
    _seed_files(project / "3mf", spec.slice_files, payload=b"z" * 300)
    _seed_files(project / "images", spec.images, payload=b"i" * 50)
    if spec.notes is not None:
        (project / "notes.md").write_text(spec.notes, encoding="utf-8")
    return project


def _kwarg_list(kwargs: dict[str, object], key: str) -> list[str]:
    value = kwargs.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        msg = f"{key} must be a list[str]"
        raise TypeError(msg)
    return [str(item) for item in value]


def _kwarg_str(kwargs: dict[str, object], key: str) -> str | None:
    value = kwargs.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        msg = f"{key} must be str"
        raise TypeError(msg)
    return value


def _seed_files(directory: Path, names: list[str], *, payload: bytes) -> None:
    for name in names:
        (directory / name).write_bytes(payload)
