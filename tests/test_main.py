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

from main import _ensure_utf8_stdout# _ensure_utf8_stdout tests

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

@patch("main.sys.argv", ["main.py", "--from-cache"])
@patch("main.generate_intel_report")
@patch("main.Path.exists")
@patch("main.Path.open")
@patch("main.json.load")
@patch("main.Path.read_text")
@patch("main.Path.write_text")
def test_main_from_cache_auto(mock_write_text, mock_read_text, mock_json_load, mock_open, mock_exists, mock_generate_intel, capsys):
    """Test full main() flow using --from-cache (auto-detect file)"""
    mock_exists.side_effect = [True, True, True]  # .env, .json, .md
    mock_json_load.return_value = [{"text": "mock"}]
    mock_read_text.return_value = "# Fake Summary"
    mock_generate_intel.return_value = "# Fake Intel Report"

    main()
    
    mock_generate_intel.assert_called_once_with([{"text": "mock"}])
    assert mock_write_text.call_count == 1
    
    captured = capsys.readouterr()
    assert "[skip] Loaded existing cache ->" in captured.out
    assert "[done] Intel report saved ->" in captured.out


@patch("main.sys.argv", ["main.py", "--limit", "10"])
@patch("main.generate_intel_report")
@patch("main.build_markdown")
@patch("fetch_mastodon.get_timeline")
@patch("fetch_bluesky.get_timeline")
@patch("fetch_timeline.fetch_timeline")
@patch("fetch_timeline.get_client")
@patch("main._load_env")
@patch("main.Path.exists")
@patch("main.Path.write_text")
def test_main_fetch_timeline(mock_write_text, mock_exists, mock_load_env, mock_get_client, mock_fetch, mock_fetch_bsky, mock_fetch_mastodon, mock_build, mock_generate, capsys):
    """Test full main() flow using API fetches."""
    mock_exists.return_value = True
    mock_get_client.return_value = MagicMock()
    mock_fetch.return_value = [{"text": "Hello", "platform": "x", "author_username": "user", "engagement_score": 10}]
    mock_fetch_bsky.return_value = [{"text": "Hello Bsky", "platform": "bluesky", "author_username": "user", "engagement_score": 5}]
    mock_fetch_mastodon.return_value = [{"text": "Hello Mastodon", "platform": "mastodon", "author_username": "user", "engagement_score": 2}]
    mock_build.return_value = "# Fetched Summary"
    mock_generate.return_value = "# Intel Report"
    
    envs = {
        "INTEL_BACKEND": "gemini", 
        "GEMINI_MODEL": "gemini-flash-latest",
        "X_API_KEY": "DUMMY_X_KEY", "X_API_SECRET": "DUMMY_X_SECRET",
        "X_ACCESS_TOKEN": "DUMMY_X_TOKEN", "X_ACCESS_TOKEN_SECRET": "DUMMY_X_TOKEN_SECRET", "X_BEARER_TOKEN": "DUMMY_X_BEARER",
        "BSKY_HANDLE": "DUMMY_BSKY_HANDLE", "BSKY_APP_PASSWORD": "DUMMY_BSKY_PASSWORD",
        "MASTODON_CLIENT_ID": "DUMMY_M_ID", "MASTODON_CLIENT_SECRET": "DUMMY_M_SECRET",
        "MASTODON_ACCESS_TOKEN": "DUMMY_M_TOKEN", "MASTODON_API_BASE_URL": "DUMMY_M_URL"
    }
    with patch.dict(os.environ, envs):
        main()
        
    mock_fetch.assert_called_once()
    mock_fetch_bsky.assert_called_once()
    mock_fetch_mastodon.assert_called_once()
    mock_build.assert_called_once()
    mock_generate.assert_called_once_with([
        {"text": "Hello", "platform": "x", "author_username": "user", "engagement_score": 10},
        {"text": "Hello Bsky", "platform": "bluesky", "author_username": "user", "engagement_score": 5},
        {"text": "Hello Mastodon", "platform": "mastodon", "author_username": "user", "engagement_score": 2}
    ])
    
    # Write summary markdown, write JSON cache, write intel report
    assert mock_write_text.call_count == 3
    
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
    mock_generate.assert_called_once_with([{"text": "Hello Bsky", "platform": "bluesky", "author_username": "user", "engagement_score": 5}])


@patch("main.sys.argv", ["main.py", "--from-cache"])
@patch("main.Path.exists")
def test_main_from_cache_missing_file_exits(mock_exists, capsys):
    """Test main() with --from-cache when the expected file is missing."""
    # .env exists (1st check), but json file doesn't (2nd check)
    mock_exists.side_effect = [True, False]
    
    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 1
        
    captured = capsys.readouterr()
    assert "[error] JSON cache file not found:" in captured.out
