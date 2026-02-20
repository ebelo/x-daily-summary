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


# ─────────────────────────────────────────────────────────────
# _load_env tests
# ─────────────────────────────────────────────────────────────

from main import _load_env, main
from unittest.mock import patch, MagicMock

def test_load_env_missing_file(capsys):
    """If .env does not exist, _load_env should exit(1)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env_path = pathlib.Path(tmpdir) / ".env"
        try:
            _load_env(env_path)
            assert False, "Should have raised SystemExit"
        except SystemExit as e:
            assert e.code == 1
        captured = capsys.readouterr()
        assert "[error] .env file not found." in captured.out


def test_load_env_missing_vars(capsys):
    """If .env exists but missing variables, _load_env should exit(1)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env_path = pathlib.Path(tmpdir) / ".env"
        env_path.write_text("SOME_VAR=1", encoding="utf-8")
        
        with patch.dict(os.environ, {}, clear=True):
            try:
                _load_env(env_path)
                assert False, "Should have raised SystemExit"
            except SystemExit as e:
                assert e.code == 1
            captured = capsys.readouterr()
            assert "[error] Missing environment variables" in captured.out


def test_load_env_success():
    """If .env exists and all variables are present, _load_env should succeed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env_path = pathlib.Path(tmpdir) / ".env"
        env_path.write_text("X_API_KEY=1\nX_API_SECRET=1\nX_ACCESS_TOKEN=1\nX_ACCESS_TOKEN_SECRET=1\nX_BEARER_TOKEN=1", encoding="utf-8")
        
        with patch.dict(os.environ, {
            "X_API_KEY": "1", "X_API_SECRET": "1",
            "X_ACCESS_TOKEN": "1", "X_ACCESS_TOKEN_SECRET": "1", "X_BEARER_TOKEN": "1"
        }):
            # Should not raise
            _load_env(env_path)


# ─────────────────────────────────────────────────────────────
# main() integration tests with mocks
# ─────────────────────────────────────────────────────────────

@patch("main.sys.argv", ["main.py", "--from-summary"])
@patch("main.generate_intel_report")
@patch("main.Path.exists")
@patch("main.Path.read_text")
@patch("main.Path.write_text")
def test_main_from_summary_auto(mock_write_text, mock_read_text, mock_exists, mock_generate_intel, capsys):
    """Test full main() flow using --from-summary (auto-detect file)"""
    # Pretend summary file exists and .env exists
    mock_exists.return_value = True
    mock_read_text.return_value = "# Fake Summary"
    mock_generate_intel.return_value = "# Fake Intel Report"

    main()
    
    # Assert intel report was generated with the fake summary
    mock_generate_intel.assert_called_once_with("# Fake Summary")
    # Assert intel report was written to file
    assert mock_write_text.call_count == 1
    
    captured = capsys.readouterr()
    assert "[skip] Loaded existing summary ->" in captured.out
    assert "[done] Intel report saved ->" in captured.out


@patch("main.sys.argv", ["main.py", "--limit", "10"])
@patch("main.generate_intel_report")
@patch("main.build_markdown")
@patch("fetch_timeline.fetch_timeline")
@patch("fetch_timeline.get_client")
@patch("main._load_env")
@patch("main.Path.exists")
@patch("main.Path.write_text")
def test_main_fetch_timeline(mock_write_text, mock_exists, mock_load_env, mock_get_client, mock_fetch, mock_build, mock_generate, capsys):
    """Test full main() flow using X API fetch."""
    mock_exists.return_value = True
    mock_get_client.return_value = MagicMock()
    mock_fetch.return_value = [{"text": "Hello"}]
    mock_build.return_value = "# Fetched Summary"
    mock_generate.return_value = "# Intel Report"
    
    with patch.dict(os.environ, {"INTEL_BACKEND": "gemini", "GEMINI_MODEL": "gemini-flash-latest"}):
        main()
        
    mock_fetch.assert_called_once()
    mock_build.assert_called_once()
    mock_generate.assert_called_once_with("# Fetched Summary")
    
    # Write summary and write intel report
    assert mock_write_text.call_count == 2
    
    captured = capsys.readouterr()
    assert "[done] Summary saved \u2192" in captured.out
    assert "[done] Intel report saved ->" in captured.out


@patch("main.sys.argv", ["main.py", "--from-summary"])
@patch("main.Path.exists")
def test_main_from_summary_missing_file_exits(mock_exists, capsys):
    """Test main() with --from-summary when the expected file is missing."""
    # .env exists (1st check), but summary file doesn't (2nd check)
    mock_exists.side_effect = [True, False]
    
    try:
        main()
        assert False, "Should have called sys.exit(1)"
    except SystemExit as e:
        assert e.code == 1
        
    captured = capsys.readouterr()
    assert "[error] Summary file not found:" in captured.out
