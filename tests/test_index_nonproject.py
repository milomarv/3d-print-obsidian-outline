"""Non-project folders render a children listing only."""

from __future__ import annotations

from typing import TYPE_CHECKING

from print_outline.index import IndexInputs, generate_index
from tests.conftest import make_project

if TYPE_CHECKING:
    from pathlib import Path

    from print_outline.config import Config


def test_root_lists_projects_subfolder(vault: Path, config: Config) -> None:
    make_project(vault / "projects", "keychain", cad=["a.step"])
    body = generate_index(IndexInputs(folder=vault, vault=vault, config=config, spoolman=None))
    assert "## Folders" in body
    assert "[[projects/projects|projects]]" in body


def test_projects_root_lists_children(vault: Path, config: Config) -> None:
    make_project(vault / "projects", "keychain", cad=["a.step"])
    make_project(vault / "projects", "spool-holder", stl=["body.stl"])
    body = generate_index(
        IndexInputs(folder=vault / "projects", vault=vault, config=config, spoolman=None),
    )
    assert "[[projects/keychain/keychain|keychain]]" in body
    assert "[[projects/spool-holder/spool-holder|spool-holder]]" in body


def test_non_project_folder_omits_file_tables(vault: Path, config: Config) -> None:
    (vault / "projects" / "wip").mkdir()
    body = generate_index(
        IndexInputs(folder=vault / "projects" / "wip", vault=vault, config=config, spoolman=None),
    )
    assert "## CAD" not in body
    assert "## Filaments" not in body


def test_notes_in_non_project_folder_listed(vault: Path, config: Config) -> None:
    (vault / "projects" / "wip").mkdir()
    (vault / "projects" / "wip" / "ideas.md").write_text("# Ideas\n", encoding="utf-8")
    body = generate_index(
        IndexInputs(folder=vault / "projects" / "wip", vault=vault, config=config, spoolman=None),
    )
    assert "## Notes" in body
    assert "[[projects/wip/ideas|ideas]]" in body


def test_timelapses_are_grouped_by_filename_month_and_newest_ten_embedded(
    vault: Path,
    config: Config,
) -> None:
    folder = vault / "timelapses"
    folder.mkdir()
    filenames = [f"video_2025-01-{day:02d}_12-00-00.mp4" for day in range(1, 12)]
    filenames.extend(["video_2024-12-31_23-59-59.mp4", "misc.mp4"])
    expected_embeds = 10
    for filename in filenames:
        (folder / filename).write_bytes(b"video")

    body = generate_index(IndexInputs(folder=folder, vault=vault, config=config, spoolman=None))

    assert body.index("### 2025-01") < body.index("### 2024-12") < body.index("### Undated")
    assert body.index("2025-01-11 12:00:00") < body.index("2025-01-10 12:00:00")
    assert body.count("  ![[") == expected_embeds
    assert sum(line.startswith("- Filename date:") for line in body.splitlines()) == len(filenames)
    assert "Filename date: unknown — [[timelapses/misc.mp4|misc.mp4]]" in body
    assert "Filename date: 2025-01-11 12:00:00" in body


def test_nested_timelapses_folder_does_not_get_timelapse_overview(
    vault: Path,
    config: Config,
) -> None:
    folder = vault / "projects" / "unrelated" / "timelapses"
    folder.mkdir(parents=True)
    (folder / "video_2025-01-01_12-00-00.mp4").write_bytes(b"video")

    body = generate_index(IndexInputs(folder=folder, vault=vault, config=config, spoolman=None))

    assert "## Timelapses" not in body
    assert "video_2025-01-01_12-00-00.mp4" not in body
