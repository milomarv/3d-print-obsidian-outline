"""Small pure helpers for size / date / wikilink formatting."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_BINARY_UNITS = ("B", "KiB", "MiB", "GiB", "TiB", "PiB")
_KIB = 1024.0


def human_size(num_bytes: int) -> str:
    """Render a binary-suffix size like `1.0 KiB`, `2.4 MiB`."""
    if num_bytes < 0:
        msg = "byte count cannot be negative"
        raise ValueError(msg)
    size = float(num_bytes)
    unit_index = 0
    while size >= _KIB and unit_index < len(_BINARY_UNITS) - 1:
        size /= _KIB
        unit_index += 1
    if unit_index == 0:
        return f"{int(size)} {_BINARY_UNITS[0]}"
    return f"{size:.1f} {_BINARY_UNITS[unit_index]}"


def iso_date(timestamp: float) -> str:
    """Render a unix mtime as `YYYY-MM-DD`. Date only — keeps diffs stable."""
    return dt.datetime.fromtimestamp(timestamp, tz=dt.UTC).date().isoformat()


def wikilink_target(rel: Path) -> str:
    """Render an Obsidian-friendly relative target. Forward slashes; no extension stripping."""
    return rel.as_posix()


def md_table_row(*cells: str) -> str:
    return "| " + " | ".join(cell.replace("|", r"\|") for cell in cells) + " |"
