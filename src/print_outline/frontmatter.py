"""Read YAML frontmatter from project folder-note index files.

Project frontmatter lives at the top of the project's own index file (above
the AUTO fence), so it is preserved across regenerations and travels with the
project.

Tag-based source of truth: the integer priority and the project state are
encoded as `prio/<N>` and `state/<value>` entries inside the inline `tags:`
list. The inline form is enforced by `ensure_default_tags` so substring
tag-search (e.g. `prio/3`, `state/ongoing`) always hits.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from pathlib import Path

_FRONTMATTER = re.compile(r"^---\s*\n(.*?\n)---\s*(?:\n|$)", re.DOTALL)

DEFAULT_STATE = "idea"
VALID_STATES: tuple[str, ...] = ("idea", "ongoing", "finished")


def read_filaments(path: Path) -> list[int]:
    """Return the list of spool IDs declared in the file's frontmatter."""
    raw = _read_value(path, "filaments")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, int) and not isinstance(item, bool)]


def read_priority(path: Path) -> int:
    """Return the project's priority, parsed from the `prio/<N>` tag.

    Higher = more important. 0 = none. Negative or unparseable values
    yield 0; otherwise unbounded.
    """
    for tag in _read_tags(path):
        if not tag.startswith("prio/"):
            continue
        try:
            return max(0, int(tag.split("/", 1)[1]))
        except (ValueError, IndexError):
            continue
    return 0


def read_state(path: Path) -> str:
    """Return the project's state, parsed from the `state/<value>` tag.

    Defaults to "idea" if no `state/*` tag is present. Values other than
    `idea`/`ongoing`/`finished` are returned verbatim — manifest filters
    compare against literals so foreign values fall through cleanly.
    """
    for tag in _read_tags(path):
        if tag.startswith("state/"):
            value = tag.split("/", 1)[1]
            return value or DEFAULT_STATE
    return DEFAULT_STATE


def ensure_default_tags(path: Path) -> bool:
    """Seed `prio/<N>` and `state/<value>` tags on the file if missing.

    - If no `prio/*` tag exists: insert `prio/<N>` using the legacy
      `priority:` integer if present, else `prio/0`.
    - If no `state/*` tag exists: insert `state/idea`.
    - Strips any legacy `priority:` integer field from the frontmatter
      once a `prio/*` tag is in place — tags are now the source of truth
      and the integer is dead data.
    - Always emits inline list form (`tags: [prio/3, state/ongoing]`); a
      multi-line `tags:` block is flattened.

    Returns True iff the file was rewritten.
    """
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER.match(text)
    if not match:
        return False
    block = match.group(1)
    try:
        data = yaml.safe_load(block) or {}
    except yaml.YAMLError:
        data = {}
    if not isinstance(data, dict):
        data = {}

    raw_tags = data.get("tags")
    if isinstance(raw_tags, list):
        existing = [str(t) for t in raw_tags if isinstance(t, (str, int))]
    elif isinstance(raw_tags, str):
        existing = [raw_tags]
    else:
        existing = []

    has_prio = any(t.startswith("prio/") for t in existing)
    has_state = any(t.startswith("state/") for t in existing)

    new_tags = list(existing)
    if not has_prio:
        legacy = data.get("priority")
        if isinstance(legacy, int) and not isinstance(legacy, bool) and legacy >= 0:
            new_tags.insert(0, f"prio/{legacy}")
        else:
            new_tags.insert(0, "prio/0")
    if not has_state:
        prio_idx = next(
            (i for i, t in enumerate(new_tags) if t.startswith("prio/")),
            -1,
        )
        new_tags.insert(prio_idx + 1, f"state/{DEFAULT_STATE}")

    legacy_priority_present = "priority" in data
    needs_tags_rewrite = (
        new_tags != existing
        or not isinstance(raw_tags, list)
        or _is_multiline_tags(block)
    )

    if not legacy_priority_present and not needs_tags_rewrite:
        return False

    new_block = block
    if needs_tags_rewrite:
        formatted = "[" + ", ".join(new_tags) + "]"
        new_block = _replace_or_append_key(new_block, "tags", formatted)
    if legacy_priority_present:
        new_block = _strip_key(new_block, "priority")

    new_text = f"---\n{new_block}---\n{text[match.end() :]}"
    if new_text == text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


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
        body = text[match.end() :]
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


def _is_multiline_tags(block: str) -> bool:
    """Detect a multi-line `tags:` block-list (`tags:\\n  - foo`)."""
    lines = block.split("\n")
    pattern = re.compile(r"^tags\s*:\s*$")
    for i, line in enumerate(lines):
        if not pattern.match(line):
            continue
        j = i + 1
        while j < len(lines) and (
            lines[j].startswith((" ", "\t")) or lines[j].lstrip().startswith("- ")
        ):
            if lines[j].lstrip().startswith("- "):
                return True
            j += 1
        return False
    return False


def _strip_key(block: str, key: str) -> str:
    """Remove a top-level key (and any block-list continuation) from a YAML block."""
    lines = block.split("\n")
    out: list[str] = []
    pattern = re.compile(rf"^{re.escape(key)}\s*:")
    i = 0
    removed = False
    while i < len(lines):
        line = lines[i]
        if not removed and pattern.match(line):
            removed = True
            i += 1
            while i < len(lines) and (
                lines[i].startswith((" ", "\t")) or lines[i].lstrip().startswith("- ")
            ):
                i += 1
            continue
        out.append(line)
        i += 1
    result = "\n".join(out)
    if not result.endswith("\n"):
        result += "\n"
    return result


def _replace_or_append_key(block: str, key: str, inline_value: str) -> str:
    """Replace a top-level `key`'s value with `key: inline_value`, or append it.

    Handles two YAML shapes: an inline value on the same line (`key: foo`),
    or a multi-line block-list continuation (`key:` followed by indented
    `- item` lines). Continuation lines are dropped on replace, since we
    always emit inline form.
    """
    lines = block.split("\n")
    out: list[str] = []
    pattern = re.compile(rf"^{re.escape(key)}\s*:")
    found = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if not found and pattern.match(line):
            out.append(f"{key}: {inline_value}")
            found = True
            i += 1
            while i < len(lines) and (
                lines[i].startswith((" ", "\t")) or lines[i].lstrip().startswith("- ")
            ):
                i += 1
            continue
        out.append(line)
        i += 1
    if not found:
        if out and out[-1] == "":
            out.insert(len(out) - 1, f"{key}: {inline_value}")
        else:
            out.append(f"{key}: {inline_value}")
    result = "\n".join(out)
    if not result.endswith("\n"):
        result += "\n"
    return result


def _read_tags(path: Path) -> list[str]:
    """Return the file's `tags:` entries as strings. Empty list if absent or malformed."""
    raw = _read_value(path, "tags")
    if isinstance(raw, list):
        return [str(t) for t in raw if isinstance(t, (str, int))]
    if isinstance(raw, str):
        return [raw]
    return []


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
