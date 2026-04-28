"""Read YAML frontmatter from project folder-note index files.

Project frontmatter lives at the top of the project's own index file (above
the AUTO fence), so it is preserved across regenerations and travels with the
project.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from pathlib import Path

_FRONTMATTER = re.compile(r"^---\s*\n(.*?\n)---\s*(?:\n|$)", re.DOTALL)


def read_filaments(path: Path) -> list[int]:
    """Return the list of spool IDs declared in the file's frontmatter."""
    raw = _read_value(path, "filaments")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, int) and not isinstance(item, bool)]


def read_priority(path: Path) -> int:
    """Return the project's priority. Higher = more important. 0 = none.

    Negative or non-int values are clamped to 0; otherwise unbounded.
    """
    raw = _read_value(path, "priority")
    if not isinstance(raw, int) or isinstance(raw, bool):
        return 0
    return max(0, raw)


def ensure_project_frontmatter(path: Path, defaults: dict[str, str]) -> bool:
    """Ensure each `defaults` key exists in `path`'s frontmatter.

    Adds missing keys verbatim with the given default string values, without
    touching existing keys or order. Creates a frontmatter block if absent.
    Returns True when the file was rewritten.
    """
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    match = _FRONTMATTER.match(text)
    if match:
        try:
            data = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            data = {}
        if not isinstance(data, dict):
            data = {}
        missing = [(k, v) for k, v in defaults.items() if k not in data]
        if not missing:
            return False
        existing_block = match.group(1).rstrip("\n")
        added = "\n".join(f"{k}: {v}" for k, v in missing)
        body = text[match.end():]
        new_text = f"---\n{existing_block}\n{added}\n---\n{body}"
    else:
        if not defaults:
            return False
        block = "\n".join(f"{k}: {v}" for k, v in defaults.items())
        new_text = f"---\n{block}\n---\n\n{text}" if text else f"---\n{block}\n---\n"
    if new_text == text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def _read_value(path: Path, key: str) -> object:
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = _FRONTMATTER.match(text)
    if match is None:
        return None
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    return data.get(key)
