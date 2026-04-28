"""Command-line entry point. Walks the vault, regenerates each `_index.md`."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from print_outline.config import Config, resolve_config
from print_outline.fence import FenceLayout
from print_outline.index import IndexInputs, generate_index
from print_outline.render import WriteResult, write_with_fence
from print_outline.spoolman import SpoolmanClient
from print_outline.walker import walk_vault

logger = logging.getLogger("print_outline")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="outline",
        description="Regenerate Obsidian _index.md files for a 3D-printing vault.",
    )
    parser.add_argument("vault", type=Path, help="Path to the vault root.")
    parser.add_argument("--config", type=Path, default=None, help="Override config file path.")
    parser.add_argument("--dry-run", action="store_true", help="Print diffs; do not write.")
    parser.add_argument("--no-spoolman", action="store_true", help="Skip Spoolman lookups.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging.")
    return parser.parse_args(argv)


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
    layout = FenceLayout(
        header=config.header,
        fence_begin=config.fence_begin,
        fence_end=config.fence_end,
    )
    spoolman = _build_spoolman(config, disabled_by_flag=args.no_spoolman)

    changed_count = 0
    total_count = 0
    for folder in walk_vault(vault, config):
        total_count += 1
        body = generate_index(
            IndexInputs(
                folder=folder.path,
                vault=vault,
                config=config,
                spoolman=spoolman,
            ),
        )
        result = write_with_fence(
            folder.path / "_index.md",
            body,
            layout,
            dry_run=args.dry_run,
        )
        _emit_result(result, dry_run=args.dry_run)
        if result.changed:
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
