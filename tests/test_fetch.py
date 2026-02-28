"""
tests/test_fetch.py
Tests for XFetcher (via the fetchers.x_fetcher module), and also the
backward-compatible fetch_timeline module wrapper.
"""

import pytest
from unittest.mock import MagicMock
from fetchers.x_fetcher import XFetcher


def _make_fetcher() -> XFetcher:
    return XFetcher()


def test_fetch_posts_with_limit(mocker):
    """XFetcher.fetch_posts respects the limit argument."""
    fetcher = _make_fetcher()
    mock_client = MagicMock()

    mock_tweet = MagicMock()
    mock_tweet.id = 123
    mock_tweet.text = "Mock post"
    mock_tweet.created_at = "2026-02-20T10:00:00Z"
    mock_tweet.author_id = 456
    mock_tweet.public_metrics = {"like_count": 10, "retweet_count": 2, "reply_count": 1}

    mock_user = MagicMock()
    mock_user.id = 456
    mock_user.name = "Tester"
    mock_user.username = "test_user"

    mock_response = MagicMock()
    mock_response.data = [mock_tweet]
    mock_response.includes = {"users": [mock_user]}
    mock_response.meta = {"next_token": None}

    mock_client.get_home_timeline.return_value = mock_response

    posts = fetcher._fetch_timeline(mock_client, limit=1)

    assert len(posts) == 1
    assert posts[0]["author_username"] == "test_user"
    assert posts[0]["text"] == "Mock post"

    mock_client.get_home_timeline.assert_called_once()
    _, kwargs = mock_client.get_home_timeline.call_args
    assert kwargs["max_results"] == 1


def test_fetch_posts_pagination(mocker):
    """XFetcher._fetch_timeline follows pagination tokens."""
    fetcher = _make_fetcher()
    mock_client = MagicMock()

    mock_tweet1 = MagicMock(id=1, text="T1", author_id=456, public_metrics={}, created_at="2026-02-20T09:00:00Z")
    mock_response1 = MagicMock(data=[mock_tweet1], includes={"users": []}, meta={"next_token": "token2"})

    mock_tweet2 = MagicMock(id=2, text="T2", author_id=456, public_metrics={}, created_at="2026-02-20T08:00:00Z")
    mock_response2 = MagicMock(data=[mock_tweet2], includes={"users": []}, meta={"next_token": None})

    mock_client.get_home_timeline.side_effect = [mock_response1, mock_response2]

    posts = fetcher._fetch_timeline(mock_client, limit=2)

    assert len(posts) == 2
    assert mock_client.get_home_timeline.call_count == 2


# ------------------------------------------------------------------
# Backward-compat wrapper still works
# ------------------------------------------------------------------

def test_legacy_fetch_timeline_wrapper(mocker):
    """fetch_timeline module wrapper delegates to XFetcher under the hood."""
    from fetch_timeline import fetch_timeline

    mock_client = MagicMock()
    mock_tweet = MagicMock(
        id=99, text="Legacy", author_id=1,
        public_metrics={"like_count": 0, "retweet_count": 0, "reply_count": 0},
        created_at="2026-02-20T10:00:00Z",
    )
    mock_response = MagicMock(data=[mock_tweet], includes={"users": []}, meta={"next_token": None})
    mock_client.get_home_timeline.return_value = mock_response

    posts = fetch_timeline(mock_client, limit=1)
    assert len(posts) == 1
    assert posts[0]["text"] == "Legacy"
