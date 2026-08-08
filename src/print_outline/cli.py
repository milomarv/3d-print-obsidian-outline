"""Command-line entry point. Walks the vault, regenerates each folder-note index."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from print_outline.config import Config, resolve_config
from print_outline.fence import FenceLayout
from print_outline.frontmatter import ensure_default_tags, ensure_project_frontmatter, read_priority
from print_outline.index import IndexInputs, generate_index
from print_outline.manifest import MANIFEST_STATES, manifest_path, render_priorities_manifest
from print_outline.render import WriteResult, write_with_fence
from print_outline.spoolman import SpoolmanClient
from print_outline.walker import (
    ensure_marker_subdirs,
    index_filename_for,
    is_excluded_dir,
    is_project,
    under_project_root,
    walk_vault,
)

if TYPE_CHECKING:
    from print_outline.walker import Folder

_PROJECT_FRONTMATTER_DEFAULTS = {"filaments": "[]", "tags": "[prio/0, state/idea]"}

logger = logging.getLogger("print_outline")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="outline",
        description="Regenerate Obsidian folder-note indexes for a 3D-printing vault.",
    )
    parser.add_argument("vault", type=Path, help="Path to the vault root.")
    parser.add_argument("--config", type=Path, default=None, help="Override config file path.")
    parser.add_argument("--dry-run", action="store_true", help="Print diffs; do not write.")
    parser.add_argument("--no-spoolman", action="store_true", help="Skip Spoolman lookups.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging.")
    return parser.parse_args(argv)


def _vault_root_error(vault: Path, config: Config) -> str | None:
    """Return an error message if `vault` doesn't look like a 3d-print vault root.

    The tool indexes an existing ``<vault>/<project_root>/`` tree. Pointing it at
    a parent directory (e.g. the whole Obsidian vault instead of the ``3d-print/``
    subfolder) silently walks unrelated folders and writes a stray manifest, so
    refuse loudly — and, when the intended subfolder is obvious, name it.
    """
    if (vault / config.project_root).is_dir():
        return None
    for child in sorted(p for p in vault.iterdir() if p.is_dir()):
        if (child / config.project_root).is_dir():
            return (
                f"vault root {vault} has no {config.project_root!r} directory, "
                f"but {child} does — did you mean to point outline at {child}?"
            )
    return (
        f"vault root {vault} has no {config.project_root!r} directory; refusing to "
        f"run. Pass the 3d-print vault root (the folder containing "
        f"{config.project_root!r}/ and {config.maintenance_root!r}/)."
    )


def _has_buildable_children(folder: Path, vault: Path, config: Config) -> bool:
    """Whether `folder` contains a child that is itself a build (project or prioritised).

    Such a folder is a grouping/parent (e.g. `bash-guard-chain-guards`, which holds
    the `bash-guard` and `chain-guard` builds) and must NOT get its own marker
    subdirs — the builds live in the children. Detected via the same project/prio
    signal scaffolding uses, so it holds even before the children are scaffolded.
    """
    for child in sorted(folder.iterdir()):
        if not child.is_dir() or is_excluded_dir(child.name, config):
            continue
        if child.name in config.marker_subdirs:
            continue
        if is_project(child, vault, config):
            return True
        index_path = child / index_filename_for(child, vault)
        if read_priority(index_path) > 0:
            return True
    return False


def _should_scaffold(folder: Folder, vault: Path, config: Config) -> bool:
    """Whether `folder` should get its marker subdirs (`cad/`/`stl/`/`3mf/`/`images/`).

    A folder qualifies when it is already a file-based project, or when it is a
    prioritised folder under the project root (`prio/<N>` with N > 0) — the same
    "real project" signal the priority manifests use. Two kinds of folder are
    deliberately left alone:

    - un-prioritised container folders (default `prio/0`, no files, e.g. an `mtb/`
      grouping), so they are not misclassified as projects; and
    - parent folders that hold child builds (e.g. `bash-guard-chain-guards`), even
      when prioritised — the marker subdirs belong on the leaf builds, not the
      grouping.
    """
    if not under_project_root(folder.path, vault, config):
        return False
    if folder.path.name == config.project_root:
        return False
    if _has_buildable_children(folder.path, vault, config):
        return False
    if folder.is_project:
        return True
    index_path = folder.path / index_filename_for(folder.path, vault)
    return read_priority(index_path) > 0


def _scaffold_project_dirs(vault: Path, config: Config, *, dry_run: bool) -> None:
    """Ensure every qualifying folder has its four marker subdirs.

    Runs as a pass BEFORE the index walk: creating marker subdirs mid-walk would
    make the walker treat the new dirs as folders to index, so the walk is fully
    materialised first.
    """
    for folder in list(walk_vault(vault, config)):
        if not _should_scaffold(folder, vault, config):
            continue
        missing = [sub for sub in config.marker_subdirs if not (folder.path / sub).is_dir()]
        if not missing:
            continue
        if dry_run:
            logger.info("would scaffold %s: %s", folder.path, ", ".join(missing))
        else:
            ensure_marker_subdirs(folder.path, config)
            logger.info("scaffolded %s: %s", folder.path, ", ".join(missing))


def _build_spoolman(config: Config, *, disabled_by_flag: bool) -> SpoolmanClient | None:
    if disabled_by_flag or not config.spoolman_enabled:
        return None
    try:
        return SpoolmanClient(config.spoolman_base_url, timeout_seconds=config.spoolman_timeout)
    except ValueError:
        logger.exception("invalid spoolman config; continuing without filament enrichment")
        return None


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    vault: Path = args.vault.expanduser().resolve()
    if not vault.is_dir():
        logger.error("vault path is not a directory: %s", vault)
        return 2

    config = resolve_config(vault, args.config)
    root_error = _vault_root_error(vault, config)
    if root_error is not None:
        logger.error("%s", root_error)
        return 2

    layout = FenceLayout(
        header=config.header,
        fence_begin=config.fence_begin,
        fence_end=config.fence_end,
    )
    spoolman = _build_spoolman(config, disabled_by_flag=args.no_spoolman)

    _scaffold_project_dirs(vault, config, dry_run=args.dry_run)

    changed_count = 0
    total_count = 0
    for folder in walk_vault(vault, config):
        total_count += 1
        index_path = folder.path / index_filename_for(folder.path, vault)
        if not args.dry_run:
            if is_project(folder.path, vault, config):
                ensure_project_frontmatter(index_path, _PROJECT_FRONTMATTER_DEFAULTS)
            ensure_default_tags(index_path)
        body = generate_index(
            IndexInputs(
                folder=folder.path,
                vault=vault,
                config=config,
                spoolman=spoolman,
            ),
        )
        result = write_with_fence(
            index_path,
            body,
            layout,
            dry_run=args.dry_run,
        )
        _emit_result(result, dry_run=args.dry_run)
        if result.changed:
            changed_count += 1

    for state in MANIFEST_STATES:
        manifest_result = write_with_fence(
            manifest_path(vault, config, state),
            render_priorities_manifest(vault, config, state),
            layout,
            dry_run=args.dry_run,
        )
        _emit_result(manifest_result, dry_run=args.dry_run)
        if manifest_result.changed:
            changed_count += 1

    logger.info(
        "%s %d/%d folders",
        "would update" if args.dry_run else "updated",
        changed_count,
        total_count,
    )
    return 0


def _emit_result(result: WriteResult, *, dry_run: bool) -> None:
    if not result.changed:
        logger.debug("unchanged: %s", result.path)
        return
    if dry_run:
        sys.stdout.write(result.diff)
    else:
        logger.info("wrote: %s", result.path)
