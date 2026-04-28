"""Read YAML frontmatter from notes.md to discover Spoolman spool IDs."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from pathlib import Path

_FRONTMATTER = re.compile(r"^---\s*\n(.*?\n)---\s*(?:\n|$)", re.DOTALL)


def read_filaments(notes_path: Path) -> list[int]:
    """Return the list of spool IDs declared in `notes.md` frontmatter.

    Returns an empty list if the file is missing, has no frontmatter, the
    frontmatter does not parse as YAML, or `filaments` is absent / not a list
    of ints.
    """
    raw = _read_filaments_raw(notes_path)
    return [item for item in raw if isinstance(item, int) and not isinstance(item, bool)]


def _read_filaments_raw(notes_path: Path) -> list[object]:
    if not notes_path.is_file():
        return []
    try:
        text = notes_path.read_text(encoding="utf-8")
    except OSError:
        return []
    match = _FRONTMATTER.match(text)
    if match is None:
        return []
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return []
    if not isinstance(data, dict):
        return []
    raw = data.get("filaments")
    return list(raw) if isinstance(raw, list) else []
