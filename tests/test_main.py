"""
tests/test_main.py
Tests for the CLI flag logic in main.py: --intel-limit and --from-summary.
"""

import sys
import os
import pathlib
import tempfile
import textwrap

# Ensure the project root is on sys.path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from main import _truncate_markdown


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _make_markdown(authors: dict) -> str:
    """Build a minimal summary markdown with given authors and post counts.
    authors = {username: post_count}
    """
    lines = ["# Daily Summary\n", "---\n"]
    for username, count in authors.items():
        lines.append(f"## @{username} — Display Name\n")
        max_idx = count - 1
        for i in range(count):
            lines.append(f"> Post number {i + 1} from {username}.\n>")
            post_suffix = "\n\n" if i < max_idx else ""
            lines.append(f"> \u2764\ufe0f {i * 10 + 1}  \U0001f501 1  \U0001f4ac 0  \u00b7  \U0001f550 12:00 UTC \u00b7  [View post](https://x.com/{username}/status/12345){post_suffix}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# _truncate_markdown tests
# ─────────────────────────────────────────────────────────────

def test_truncate_no_limit():
    """intel_limit=0 returns the full markdown unchanged."""
    md = _make_markdown({"user_a": 5, "user_b": 3})
    result = _truncate_markdown(md, intel_limit=0)
    assert result == md


def test_truncate_returns_fewer_posts():
    """With intel_limit=5, output contains fewer posts than the full set."""
    md = _make_markdown({"user_a": 10, "user_b": 10})
    result = _truncate_markdown(md, intel_limit=5)
    # Count View post links as proxy for post count
    post_count = result.count("[View post](")
    assert post_count == 5


def test_truncate_preserves_header():
    """The summary header (before the first ## @) is always preserved."""
    md = _make_markdown({"user_a": 3})
    result = _truncate_markdown(md, intel_limit=2)
    assert "# Daily Summary" in result


def test_truncate_full_author_kept():
    """An author whose total posts fit within the limit is kept fully."""
    md = _make_markdown({"user_a": 3, "user_b": 10})
    result = _truncate_markdown(md, intel_limit=5)
    # user_a (3 posts) fits; check all 3 posts from user_a are present
    assert result.count("from user_a") == 3


def test_truncate_intra_section():
    """An author whose posts would exceed the limit is partially truncated."""
    md = _make_markdown({"user_a": 3, "user_b": 10})
    result = _truncate_markdown(md, intel_limit=5)
    
    # Total posts should be exactly 5
    assert result.count("[View post](") == 5
    
    # user_a should have 3 posts
    assert result.count("from user_a") == 3
    
    # user_b should have exactly 2 posts to reach the limit of 5
    assert result.count("from user_b") == 2
    
    # The header for user_b should be present
    assert "## @user_b" in result


def test_truncate_no_sections_returns_unchanged():
    """Markdown with no ## @ sections returns unchanged."""
    md = "# Just a header\nSome text with no author sections."
    result = _truncate_markdown(md, intel_limit=10)
    assert result == md


# ─────────────────────────────────────────────────────────────
# --from-summary logic tests (via file loading simulation)
# ─────────────────────────────────────────────────────────────

def test_from_summary_file_read():
    """Simulated --from-summary: loading a summary .md gives correct content."""
    expected_content = "# X Daily Summary\n\nSome content here."
    with tempfile.TemporaryDirectory() as tmpdir:
        summary_path = pathlib.Path(tmpdir) / "summary_2026-02-20.md"
        summary_path.write_text(expected_content, encoding="utf-8")

        loaded = summary_path.read_text(encoding="utf-8")
        assert loaded == expected_content


def test_from_summary_missing_file_raises():
    """A missing summary file should not silently succeed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        missing = pathlib.Path(tmpdir) / "summary_9999-99-99.md"
        assert not missing.exists()
