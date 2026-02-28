"""
tests/test_fetch_mastodon.py
Tests for MastodonFetcher (via fetchers.mastodon_fetcher).
"""

import pytest
import os
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from fetchers.mastodon_fetcher import MastodonFetcher
from scoring import add_z_scores


def _make_fetcher() -> MastodonFetcher:
    return MastodonFetcher()


# ------------------------------------------------------------------
# is_configured
# ------------------------------------------------------------------

def test_is_configured_true():
    envs = {
        "MASTODON_CLIENT_ID": "DUMMY_ID",
        "MASTODON_CLIENT_SECRET": "DUMMY_SECRET",
        "MASTODON_ACCESS_TOKEN": "DUMMY_TOKEN",
        "MASTODON_API_BASE_URL": "https://mastodon.social",
    }
    with patch.dict(os.environ, envs):
        assert _make_fetcher().is_configured() is True


def test_is_configured_false():
    with patch.dict(os.environ, {}, clear=True):
        assert _make_fetcher().is_configured() is False


# ------------------------------------------------------------------
# _get_client
# ------------------------------------------------------------------

def test_get_client_success():
    with patch.dict(os.environ, {
        "MASTODON_CLIENT_ID": "dummy_client_id",
        "MASTODON_CLIENT_SECRET": "dummy_secret",
        "MASTODON_ACCESS_TOKEN": "dummy_token",
        "MASTODON_API_BASE_URL": "https://mastodon.social"
    }):
        with patch("fetchers.mastodon_fetcher.Mastodon") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            client = _make_fetcher()._get_client()
            assert client == mock_client
            mock_client_cls.assert_called_once_with(
                client_id="dummy_client_id",
                client_secret="dummy_secret",
                access_token="dummy_token",
                api_base_url="https://mastodon.social",
            )


def test_get_client_missing_env():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="Missing MASTODON_CLIENT_ID"):
            _make_fetcher()._get_client()


# ------------------------------------------------------------------
# _parse_posts
# ------------------------------------------------------------------

def test_parse_posts():
    mock_toot = MagicMock()
    mock_toot.id = 123456789
    mock_toot.favourites_count = 100
    mock_toot.reblogs_count = 20
    mock_toot.replies_count = 5

    mock_account = mock_toot.account
    mock_account.display_name = "User Name"
    mock_account.username = "user"
    mock_account.acct = "user@mastodon.social"

    mock_toot.content = "<p>Hello <b>world</b></p>"
    mock_toot.created_at = datetime(2023, 10, 1, 12, 0, tzinfo=timezone.utc)
    mock_toot.url = "https://mastodon.social/@user/123456789"

    posts = _make_fetcher()._parse_posts([mock_toot])
    assert len(posts) == 1
    post = posts[0]

    assert post["id"] == "123456789"
    assert post["platform"] == "mastodon"
    assert post["author_username"] == "user@mastodon.social"
    assert post["author_name"] == "User Name"
    assert post["text"] == "Hello world"
    assert post["likes"] == 100
    assert post["reposts"] == 20
    assert post["replies"] == 5
    # Engagement: (100*2) + (20*3) + 5 = 265
    assert post["engagement_score"] == 265
    assert post["url"] == "https://mastodon.social/@user/123456789"
    assert post["created_at"] == datetime(2023, 10, 1, 12, 0, tzinfo=timezone.utc)


# ------------------------------------------------------------------
# fetch_posts
# ------------------------------------------------------------------

@patch("fetchers.mastodon_fetcher.MastodonFetcher._get_client")
def test_fetch_posts_with_limit(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    dummy_toots = []
    for i in range(15):
        toot = MagicMock()
        toot.id = i
        toot.favourites_count = i
        toot.reblogs_count = 0
        toot.replies_count = 0
        toot.content = f"Post {i}"
        toot.created_at = datetime(2023, 10, 1, 12, i % 60, tzinfo=timezone.utc)
        toot.url = f"https://example.com/{i}"
        account = toot.account
        account.acct = f"user{i}"
        account.display_name = f"User {i}"
        dummy_toots.append(toot)

    mock_client.timeline_home.return_value = dummy_toots

    posts = _make_fetcher().fetch_posts(limit=10)

    assert len(posts) == 10
    mock_client.timeline_home.assert_called_once_with(limit=40)


@patch("fetchers.mastodon_fetcher.MastodonFetcher._get_client")
def test_fetch_posts_with_time_window(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    # Post 1 hour ago (inside 24h window)
    toot1 = MagicMock(id=1, favourites_count=0, reblogs_count=0, replies_count=0,
                      content="Inside", url="u1")
    toot1.created_at = datetime(2023, 10, 2, 11, 0, tzinfo=timezone.utc)
    toot1.account.acct = "user1"
    toot1.account.display_name = "User 1"

    # Post 48 hours ago (outside 24h window)
    toot2 = MagicMock(id=2, favourites_count=0, reblogs_count=0, replies_count=0,
                      content="Outside", url="u2")
    toot2.created_at = datetime(2023, 9, 30, 12, 0, tzinfo=timezone.utc)
    toot2.account.acct = "user2"
    toot2.account.display_name = "User 2"

    mock_client.timeline_home.return_value = [toot1, toot2]

    with patch("fetchers.mastodon_fetcher.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2023, 10, 2, 12, 0, tzinfo=timezone.utc)
        mock_datetime.side_effect = lambda *a, **kw: datetime(*a, **kw)
        posts = _make_fetcher().fetch_posts(hours=24)

    assert len(posts) == 1
    assert posts[0]["text"] == "Inside"


