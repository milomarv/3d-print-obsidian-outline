"""`## Tasks` table embedded in the maintenance folder-note."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from print_outline.index import IndexInputs, generate_index
from print_outline.maintenance import is_maintenance_folder, render_maintenance_tasks

if TYPE_CHECKING:
    from pathlib import Path

    from print_outline.config import Config


def _write_task(folder: Path, slug: str, frontmatter: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{slug}.md").write_text(frontmatter, encoding="utf-8")


def test_renders_table_with_every_task(vault: Path, config: Config) -> None:
    folder = vault / config.maintenance_root
    _write_task(
        folder,
        "run-updates",
        "---\ninterval: 1\nunit: monthly\nlast_done: 2026-02-18\n---\n",
    )
    _write_task(
        folder,
        "filament-cutter",
        "---\ninterval: 3\nunit: monthly\nlast_done: 2025-12-22\n---\n",
    )
    body = render_maintenance_tasks(folder, today=dt.date(2026, 4, 30))
    assert "[[run-updates]]" in body
    assert "[[filament-cutter]]" in body
    assert "Needs today" in body


def test_needs_today_flag(vault: Path, config: Config) -> None:
    folder = vault / config.maintenance_root
    _write_task(
        folder,
        "overdue",
        "---\ninterval: 1\nunit: monthly\nlast_done: 2026-02-01\n---\n",
    )
    _write_task(
        folder,
        "fresh",
        "---\ninterval: 1\nunit: monthly\nlast_done: 2026-04-25\n---\n",
    )
    body = render_maintenance_tasks(folder, today=dt.date(2026, 4, 30))
    overdue_line = next(line for line in body.splitlines() if "[[overdue]]" in line)
    fresh_line = next(line for line in body.splitlines() if "[[fresh]]" in line)
    assert overdue_line.endswith("| true |")
    assert fresh_line.endswith("| false |")


def test_skips_folder_note_and_malformed_tasks(vault: Path, config: Config) -> None:
    folder = vault / config.maintenance_root
    folder.mkdir(parents=True)
    (folder / "maintenance.md").write_text("# folder note\n", encoding="utf-8")
    _write_task(folder, "no-frontmatter", "")
    _write_task(folder, "missing-unit", "---\ninterval: 1\nlast_done: 2026-04-01\n---\n")
    _write_task(
        folder,
        "weird-unit",
        "---\ninterval: 1\nunit: fortnightly\nlast_done: 2026-04-01\n---\n",
    )
    _write_task(
        folder,
        "complete",
        "---\ninterval: 1\nunit: monthly\nlast_done: 2026-04-01\n---\n",
    )
    body = render_maintenance_tasks(folder, today=dt.date(2026, 4, 30))
    assert "[[complete]]" in body
    assert "[[no-frontmatter]]" not in body
    assert "[[missing-unit]]" not in body
    assert "[[weird-unit]]" not in body
    assert "[[maintenance]]" not in body


def test_handles_quoted_iso_string_dates(vault: Path, config: Config) -> None:
    folder = vault / config.maintenance_root
    _write_task(
        folder,
        "quoted",
        '---\ninterval: 1\nunit: monthly\nlast_done: "2026-04-01"\n---\n',
    )
    body = render_maintenance_tasks(folder, today=dt.date(2026, 4, 30))
    assert "2026-04-01" in body
    assert "[[quoted]]" in body


def test_renders_empty_table_when_folder_missing(vault: Path, config: Config) -> None:
    folder = vault / config.maintenance_root
    body = render_maintenance_tasks(folder, today=dt.date(2026, 4, 30))
    assert body.startswith("## Tasks")
    assert "Slug" in body
    assert "Needs today" in body


def test_is_maintenance_folder_detects_root(vault: Path, config: Config) -> None:
    assert is_maintenance_folder(vault / "maintenance", vault, config)
    assert not is_maintenance_folder(vault / "projects", vault, config)
    assert not is_maintenance_folder(vault, vault, config)


def test_index_embeds_tasks_table_in_maintenance_folder_note(
    vault: Path,
    config: Config,
) -> None:
    folder = vault / config.maintenance_root
    _write_task(
        folder,
        "real-task",
        "---\ninterval: 1\nunit: monthly\nlast_done: 2026-04-01\n---\n",
    )
    body = generate_index(
        IndexInputs(folder=folder, vault=vault, config=config, spoolman=None),
    )
    assert "## Tasks" in body
    assert "[[real-task]]" in body
    assert "## Notes" not in body


def test_non_maintenance_folder_keeps_notes_section(
    vault: Path,
    config: Config,
) -> None:
    folder = vault / "projects" / "ideas"
    folder.mkdir(parents=True)
    (folder / "draft.md").write_text("# draft\n", encoding="utf-8")
    body = generate_index(
        IndexInputs(folder=folder, vault=vault, config=config, spoolman=None),
    )
    assert "## Notes" in body
    assert "## Tasks" not in body
