"""ensure_default_tags: seeds prio/state defaults, preserves existing values, migrates legacy priority."""

from __future__ import annotations

from typing import TYPE_CHECKING

from print_outline.frontmatter import ensure_default_tags

if TYPE_CHECKING:
    from pathlib import Path


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def test_seeds_both_defaults_when_tags_absent(tmp_path: Path) -> None:
    f = tmp_path / "p.md"
    _write(f, "---\nfilaments: []\n---\n\nbody\n")
    assert ensure_default_tags(f) is True
    text = f.read_text(encoding="utf-8")
    assert "tags: [prio/0, state/idea]" in text
    assert text.endswith("\nbody\n")


def test_preserves_existing_prio_and_state(tmp_path: Path) -> None:
    f = tmp_path / "p.md"
    initial = "---\ntags: [prio/7, state/ongoing, wip]\n---\n"
    _write(f, initial)
    assert ensure_default_tags(f) is False
    assert f.read_text(encoding="utf-8") == initial


def test_adds_state_when_only_prio_present(tmp_path: Path) -> None:
    f = tmp_path / "p.md"
    _write(f, "---\ntags: [prio/3, wip]\n---\n")
    assert ensure_default_tags(f) is True
    text = f.read_text(encoding="utf-8")
    assert "tags: [prio/3, state/idea, wip]" in text


def test_adds_prio_when_only_state_present(tmp_path: Path) -> None:
    f = tmp_path / "p.md"
    _write(f, "---\ntags: [state/ongoing]\n---\n")
    assert ensure_default_tags(f) is True
    text = f.read_text(encoding="utf-8")
    assert "tags: [prio/0, state/ongoing]" in text


def test_migrates_legacy_priority_integer_to_tag(tmp_path: Path) -> None:
    f = tmp_path / "p.md"
    _write(f, "---\npriority: 5\n---\n")
    assert ensure_default_tags(f) is True
    text = f.read_text(encoding="utf-8")
    assert "tags: [prio/5, state/idea]" in text
    assert "priority:" not in text


def test_migrates_legacy_priority_alongside_existing_tags(tmp_path: Path) -> None:
    f = tmp_path / "p.md"
    _write(f, "---\npriority: 5\ntags: [wip]\n---\n")
    assert ensure_default_tags(f) is True
    text = f.read_text(encoding="utf-8")
    assert "tags: [prio/5, state/idea, wip]" in text
    assert "priority:" not in text


def test_strips_legacy_priority_when_prio_tag_already_present(tmp_path: Path) -> None:
    f = tmp_path / "p.md"
    _write(f, "---\npriority: 5\ntags: [prio/3, state/ongoing]\n---\n")
    assert ensure_default_tags(f) is True
    text = f.read_text(encoding="utf-8")
    # tag wins (already-present value preserved); legacy integer removed
    assert "tags: [prio/3, state/ongoing]" in text
    assert "priority:" not in text


def test_idempotent_when_already_in_form(tmp_path: Path) -> None:
    f = tmp_path / "p.md"
    initial = "---\ntags: [prio/3, state/ongoing]\n---\n"
    _write(f, initial)
    assert ensure_default_tags(f) is False
    assert f.read_text(encoding="utf-8") == initial


def test_flattens_multiline_tags_block(tmp_path: Path) -> None:
    f = tmp_path / "p.md"
    _write(f, "---\ntags:\n  - prio/2\n  - wip\n---\n")
    assert ensure_default_tags(f) is True
    text = f.read_text(encoding="utf-8")
    assert "tags: [prio/2, state/idea, wip]" in text
    assert "  - prio/2" not in text


def test_no_frontmatter_is_noop(tmp_path: Path) -> None:
    f = tmp_path / "p.md"
    _write(f, "no frontmatter here\n")
    assert ensure_default_tags(f) is False


def test_missing_file_is_noop(tmp_path: Path) -> None:
    f = tmp_path / "absent.md"
    assert ensure_default_tags(f) is False
