"""Fence layout writes new files and splices existing ones safely."""

from __future__ import annotations

from print_outline.fence import FenceLayout

LAYOUT = FenceLayout(
    header="<!-- AUTO-GENERATED -->",
    fence_begin="<!-- BEGIN AUTO -->",
    fence_end="<!-- END AUTO -->",
)


def test_initial_file_wraps_content() -> None:
    out = LAYOUT.initial_file("hello\nworld")
    assert out.startswith("<!-- AUTO-GENERATED -->")
    assert "<!-- BEGIN AUTO -->\nhello\nworld\n<!-- END AUTO -->\n" in out


def test_splice_replaces_only_inside_fences() -> None:
    existing = (
        "<!-- AUTO-GENERATED -->\n\n"
        "<!-- BEGIN AUTO -->\nold body\n<!-- END AUTO -->\n\n"
        "user prose below the fence\n"
    )
    out = LAYOUT.splice(existing, "new body")
    assert "old body" not in out
    assert "new body" in out
    assert "user prose below the fence" in out
    assert out.startswith("<!-- AUTO-GENERATED -->")


def test_splice_appends_when_no_fence_exists() -> None:
    existing = "stale content with no fences yet\n"
    out = LAYOUT.splice(existing, "fresh body")
    assert "stale content with no fences yet" in out
    assert "<!-- BEGIN AUTO -->\nfresh body\n<!-- END AUTO -->" in out


def test_splice_idempotent_for_same_input() -> None:
    body = "stable body"
    once = LAYOUT.initial_file(body)
    twice = LAYOUT.splice(once, body)
    assert once == twice
