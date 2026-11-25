from __future__ import annotations

from typing import TYPE_CHECKING

from print_outline.cli import main

if TYPE_CHECKING:
    from pathlib import Path

EXIT_USAGE = 2


def test_folder_target_only_updates_that_note(vault: Path) -> None:
    timelapses = vault / "timelapses"
    timelapses.mkdir()
    (timelapses / "video_2025-01-02_03-04-05.mp4").write_bytes(b"video")
    target_note = timelapses / "timelapses.md"
    target_note.write_text(
        "---\ncustom: value\n---\nBefore\n<!-- BEGIN AUTO -->\nold\n<!-- END AUTO -->\nAfter\n",
        encoding="utf-8",
    )
    unrelated_note = vault / "projects" / "keep.md"
    unrelated_note.write_text("untouched\n", encoding="utf-8")
    unrelated_content = unrelated_note.read_bytes()

    result = main([str(vault), "--folder", "timelapses", "--no-spoolman"])

    assert result == 0
    updated = target_note.read_text(encoding="utf-8")
    assert updated.startswith("---\ncustom: value\n---\nBefore\n")
    assert updated.endswith("<!-- END AUTO -->\nAfter\n")
    assert "video_2025-01-02_03-04-05.mp4" in updated
    assert unrelated_note.read_bytes() == unrelated_content
    assert not (vault / "projects" / "projects.md").exists()
    assert not (vault / "_priorities-ongoing.md").exists()


def test_folder_target_rejects_outside_or_missing_directory(vault: Path) -> None:
    outside = vault.parent / "outside"
    outside.mkdir()

    assert main([str(vault), "--folder", str(outside), "--no-spoolman"]) == EXIT_USAGE
    assert main([str(vault), "--folder", "missing", "--no-spoolman"]) == EXIT_USAGE
    assert not (vault / "_priorities-ongoing.md").exists()
