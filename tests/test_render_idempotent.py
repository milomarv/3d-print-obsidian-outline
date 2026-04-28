"""Re-rendering the same content writes nothing and preserves user edits."""

from __future__ import annotations

from typing import TYPE_CHECKING

from print_outline.fence import FenceLayout
from print_outline.render import write_with_fence

if TYPE_CHECKING:
    from pathlib import Path

LAYOUT = FenceLayout(
    header="<!-- AUTO-GENERATED -->",
    fence_begin="<!-- BEGIN AUTO -->",
    fence_end="<!-- END AUTO -->",
)


def test_initial_write_creates_file(tmp_path: Path) -> None:
    target = tmp_path / "_index.md"
    result = write_with_fence(target, "body", LAYOUT, dry_run=False)
    assert result.changed is True
    assert target.read_text(encoding="utf-8").startswith("<!-- AUTO-GENERATED -->")


def test_second_write_with_same_body_is_noop(tmp_path: Path) -> None:
    target = tmp_path / "_index.md"
    write_with_fence(target, "stable body", LAYOUT, dry_run=False)
    mtime_before = target.stat().st_mtime_ns
    bytes_before = target.read_bytes()
    result = write_with_fence(target, "stable body", LAYOUT, dry_run=False)
    assert result.changed is False
    assert target.stat().st_mtime_ns == mtime_before
    assert target.read_bytes() == bytes_before


def test_user_prose_below_end_fence_survives(tmp_path: Path) -> None:
    target = tmp_path / "_index.md"
    write_with_fence(target, "first body", LAYOUT, dry_run=False)
    text = target.read_text(encoding="utf-8") + "\n## My notes\n\nmanual prose\n"
    target.write_text(text, encoding="utf-8")
    write_with_fence(target, "second body", LAYOUT, dry_run=False)
    final = target.read_text(encoding="utf-8")
    assert "second body" in final
    assert "first body" not in final
    assert "## My notes" in final
    assert "manual prose" in final


def test_dry_run_does_not_write(tmp_path: Path) -> None:
    target = tmp_path / "_index.md"
    result = write_with_fence(target, "body", LAYOUT, dry_run=True)
    assert result.changed is True
    assert result.diff
    assert not target.exists()
