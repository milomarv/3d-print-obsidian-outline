"""Read YAML frontmatter to discover Spoolman spool IDs.

For project folders the frontmatter lives at the top of the project's own
folder-note index file (above the AUTO fence), so it is preserved across
regenerations and travels with the project.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from pathlib import Path

_FRONTMATTER = re.compile(r"^---\s*\n(.*?\n)---\s*(?:\n|$)", re.DOTALL)


def read_filaments(path: Path) -> list[int]:
    """Return the list of spool IDs declared in the file's frontmatter.

    Returns an empty list if the file is missing, has no frontmatter, the
    frontmatter does not parse as YAML, or `filaments` is absent / not a list
    of ints.
    """
    raw = _read_filaments_raw(path)
    return [item for item in raw if isinstance(item, int) and not isinstance(item, bool)]


def _read_filaments_raw(path: Path) -> list[object]:
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8")
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
