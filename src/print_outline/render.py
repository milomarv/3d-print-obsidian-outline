"""Idempotent file writer that respects the AUTO fence."""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from print_outline.fence import FenceLayout


@dataclass(frozen=True)
class WriteResult:
    """Outcome of a single fence-aware write."""

    path: Path
    changed: bool
    diff: str


def write_with_fence(
    path: Path,
    auto_block: str,
    layout: FenceLayout,
    *,
    dry_run: bool,
) -> WriteResult:
    """Write `auto_block` between fences in `path`. Skip the write when bytes are unchanged."""
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        new_text = layout.splice(existing, auto_block)
    else:
        existing = ""
        new_text = layout.initial_file(auto_block)

    if new_text == existing:
        return WriteResult(path=path, changed=False, diff="")

    diff = "".join(
        difflib.unified_diff(
            existing.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=str(path),
            tofile=str(path),
        ),
    )
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new_text, encoding="utf-8")
    return WriteResult(path=path, changed=True, diff=diff)
