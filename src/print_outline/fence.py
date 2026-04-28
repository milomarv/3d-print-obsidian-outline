"""Splice content between BEGIN/END AUTO fences without disturbing surrounding text."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class FenceLayout:
    """How the rendered file is wrapped."""

    header: str
    fence_begin: str
    fence_end: str

    def initial_file(self, auto_block: str) -> str:
        body = auto_block.rstrip()
        return f"{self.header}\n\n{self.fence_begin}\n{body}\n{self.fence_end}\n"

    def splice(self, existing: str, auto_block: str) -> str:
        """Replace the auto region in `existing`; preserve everything outside the fences."""
        pattern = re.compile(
            re.escape(self.fence_begin) + r".*?" + re.escape(self.fence_end),
            re.DOTALL,
        )
        replacement = f"{self.fence_begin}\n{auto_block.rstrip()}\n{self.fence_end}"
        match = pattern.search(existing)
        if match is None:
            trimmed = existing.rstrip("\n")
            joiner = "\n\n" if trimmed else ""
            return f"{trimmed}{joiner}{replacement}\n"
        return pattern.sub(replacement, existing, count=1)
