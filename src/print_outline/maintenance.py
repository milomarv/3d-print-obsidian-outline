"""Render a `## Tasks` section for the maintenance folder-note.

Embedded directly into `maintenance/maintenance.md`'s auto-block by
`index.py` — no separate manifest file. The table snapshots each task's
schedule fields (`interval`, `unit`, `last_done`) plus a `needs_today`
flag computed at regen time, so the maintenance skill can answer ranking
questions with a single read.
"""

from __future__ import annotations

import datetime as dt
import re
from typing import TYPE_CHECKING, Any

import yaml

from print_outline.formatting import md_table_row

if TYPE_CHECKING:
    from pathlib import Path

    from print_outline.config import Config


_FRONTMATTER = re.compile(r"^---\s*\n(.*?\n)---\s*(?:\n|$)", re.DOTALL)

_DAYS_PER_UNIT = {
    "daily": 1,
    "weekly": 7,
    "monthly": 30,
    "yearly": 365,
}


def is_maintenance_folder(path: Path, vault: Path, config: Config) -> bool:
    """Return True iff `path` is the configured maintenance root."""
    return path == vault / config.maintenance_root


def render_maintenance_tasks(folder: Path, *, today: dt.date | None = None) -> str:
    """Return the `## Tasks` section body for the maintenance folder-note."""
    today = today or dt.date.today()
    folder_note = f"{folder.name}.md"
    rows: list[tuple[str, int, str, dt.date, bool]] = []
    if folder.is_dir():
        for path in sorted(folder.iterdir()):
            if not path.is_file() or path.suffix.lower() != ".md":
                continue
            if path.name == folder_note:
                continue
            data = _read_frontmatter(path)
            interval = data.get("interval")
            unit = data.get("unit")
            last_done = _coerce_date(data.get("last_done"))
            if not isinstance(interval, int) or isinstance(interval, bool):
                continue
            if not isinstance(unit, str) or last_done is None:
                continue
            days = _DAYS_PER_UNIT.get(unit)
            if days is None:
                continue
            next_due = last_done + dt.timedelta(days=interval * days)
            needs_today = today >= next_due
            rows.append((path.stem, interval, unit, last_done, needs_today))

    rows.sort(key=lambda r: r[0])

    lines = [
        "## Tasks",
        md_table_row("Slug", "Interval", "Unit", "Last done", "Needs today"),
        md_table_row("---", "---", "---", "---", "---"),
    ]
    for slug, interval, unit, last_done, needs_today in rows:
        lines.append(
            md_table_row(
                f"[[{slug}]]",
                str(interval),
                unit,
                last_done.isoformat(),
                "true" if needs_today else "false",
            ),
        )
    return "\n".join(lines)


def _coerce_date(value: object) -> dt.date | None:
    if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
        return value
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _read_frontmatter(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    match = _FRONTMATTER.match(text)
    if not match:
        return {}
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}
    if not isinstance(data, dict):
        return {}
    return data
