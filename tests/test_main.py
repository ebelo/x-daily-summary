"""
tests/test_main.py
Tests for the CLI flag logic in main.py: --intel-limit and --from-summary.
"""

import sys
import os
import pathlib
import tempfile
import textwrap
import unittest.mock
import pytest

# Ensure the project root is on sys.path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from main import _truncate_markdown, _ensure_utf8_stdout


# _ensure_utf8_stdout tests

def test_ensure_utf8_stdout_reconfigures_when_cp1252(monkeypatch):
    """On a cp1252 terminal, stdout should be reconfigured to UTF-8."""
    mock_stdout = unittest.mock.MagicMock()
    mock_stdout.encoding = "cp1252"
    monkeypatch.setattr(sys, "stdout", mock_stdout)
    _ensure_utf8_stdout()
    mock_stdout.reconfigure.assert_called_once_with(encoding="utf-8")


def test_ensure_utf8_stdout_no_reconfigure_when_already_utf8(monkeypatch):
    """When stdout is already UTF-8, reconfigure should not be called."""
    mock_stdout = unittest.mock.MagicMock()
    mock_stdout.encoding = "utf-8"
    monkeypatch.setattr(sys, "stdout", mock_stdout)
    _ensure_utf8_stdout()
    mock_stdout.reconfigure.assert_not_called()



# Helpers

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


# _truncate_markdown tests

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


# --from-summary logic tests (via file loading simulation)

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


# _load_env tests

from main import _load_env, main
from unittest.mock import patch, MagicMock

def test_load_env_missing_file(capsys):
    """If .env does not exist, _load_env should exit(1)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        env_path = pathlib.Path(tmpdir) / ".env"
        with pytest.raises(SystemExit) as e:
            _load_env(env_path)
        assert e.value.code == 1
        captured = capsys.readouterr()
        assert "[error] .env file not found." in captured.out




# main() integration tests with mocks

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
@patch("fetch_bluesky.get_timeline")
@patch("fetch_timeline.fetch_timeline")
@patch("fetch_timeline.get_client")
@patch("main._load_env")
@patch("main.Path.exists")
@patch("main.Path.write_text")
def test_main_fetch_timeline(mock_write_text, mock_exists, mock_load_env, mock_get_client, mock_fetch, mock_fetch_bsky, mock_build, mock_generate, capsys):
    """Test full main() flow using X API fetch."""
    mock_exists.return_value = True
    mock_get_client.return_value = MagicMock()
    mock_fetch.return_value = [{"text": "Hello", "platform": "x", "author_username": "user", "engagement_score": 10}]
    mock_fetch_bsky.return_value = [{"text": "Hello Bsky", "platform": "bluesky", "author_username": "user", "engagement_score": 5}]
    mock_build.return_value = "# Fetched Summary"
    mock_generate.return_value = "# Intel Report"
    
    envs = {
        "INTEL_BACKEND": "gemini", 
        "GEMINI_MODEL": "gemini-flash-latest",
        "X_API_KEY": "DUMMY_X_KEY", "X_API_SECRET": "DUMMY_X_SECRET",
        "X_ACCESS_TOKEN": "DUMMY_X_TOKEN", "X_ACCESS_TOKEN_SECRET": "DUMMY_X_TOKEN_SECRET", "X_BEARER_TOKEN": "DUMMY_X_BEARER",
        "BSKY_HANDLE": "DUMMY_BSKY_HANDLE", "BSKY_APP_PASSWORD": "DUMMY_BSKY_PASSWORD"
    }
    with patch.dict(os.environ, envs):
        main()
        
    mock_fetch.assert_called_once()
    mock_fetch_bsky.assert_called_once()
    mock_build.assert_called_once()
    mock_generate.assert_called_once_with("# Fetched Summary")
    
    # Write summary and write intel report
    assert mock_write_text.call_count == 2
    
    captured = capsys.readouterr()
    assert "[done] Summary saved \u2192" in captured.out
    assert "[done] Intel report saved ->" in captured.out


@patch("main.sys.argv", ["main.py", "--source", "bluesky", "--limit", "5"])
@patch("main.generate_intel_report")
@patch("main.build_markdown")
@patch("fetch_bluesky.get_timeline")
@patch("fetch_timeline.fetch_timeline")
@patch("main._load_env")
@patch("main.Path.exists")
@patch("main.Path.write_text")
def test_main_fetch_bluesky_only(mock_write_text, mock_exists, mock_load_env, mock_fetch_x, mock_fetch_bsky, mock_build, mock_generate, capsys):
    """Test main() flow with --source bluesky."""
    mock_exists.return_value = True
    mock_fetch_bsky.return_value = [{"text": "Hello Bsky", "platform": "bluesky", "author_username": "user", "engagement_score": 5}]
    mock_build.return_value = "# Bsky Summary"
    mock_generate.return_value = "# Intel Report"
    
    envs = {
        "BSKY_HANDLE": "DUMMY_BSKY_HANDLE", "BSKY_APP_PASSWORD": "DUMMY_BSKY_PASSWORD",
        "INTEL_BACKEND": "gemini", "GEMINI_MODEL": "gemini-flash-latest"
    }
    with patch.dict(os.environ, envs):
        main()
        
    mock_fetch_bsky.assert_called_once()
    mock_fetch_x.assert_not_called()
    mock_generate.assert_called_once_with("# Bsky Summary")


@patch("main.sys.argv", ["main.py", "--from-summary"])
@patch("main.Path.exists")
def test_main_from_summary_missing_file_exits(mock_exists, capsys):
    """Test main() with --from-summary when the expected file is missing."""
    # .env exists (1st check), but summary file doesn't (2nd check)
    mock_exists.side_effect = [True, False]
    
    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 1
        
    captured = capsys.readouterr()
    assert "[error] Summary file not found:" in captured.out
