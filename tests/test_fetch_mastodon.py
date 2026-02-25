import pytest
import os
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from fetch_mastodon import get_client, _parse_posts, get_timeline
from scoring import add_z_scores

def test_get_client_success():
    with patch.dict(os.environ, {
        "MASTODON_CLIENT_ID": "dummy_client_id",
        "MASTODON_CLIENT_SECRET": "dummy_secret",
        "MASTODON_ACCESS_TOKEN": "dummy_token",
        "MASTODON_API_BASE_URL": "https://mastodon.social"
    }):
        with patch("fetch_mastodon.Mastodon") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            client = get_client()
            assert client == mock_client
            mock_client_cls.assert_called_once_with(
                client_id="dummy_client_id",
                client_secret="dummy_secret",
                access_token="dummy_token",
                api_base_url="https://mastodon.social"
            )

def test_get_client_missing_env():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="Missing MASTODON_CLIENT_ID"):
            get_client()

def test_parse_posts():
    mock_toot = MagicMock()
    mock_toot.id = 123456789
    mock_toot.favourites_count = 100
    mock_toot.reblogs_count = 20
    mock_toot.replies_count = 5
    
    # Mock account
    mock_account = mock_toot.account
    mock_account.display_name = "User Name"
    mock_account.username = "user"
    mock_account.acct = "user@mastodon.social"
    
    mock_toot.content = "<p>Hello <b>world</b></p>"
    mock_toot.created_at = datetime(2023, 10, 1, 12, 0, tzinfo=timezone.utc)
    mock_toot.url = "https://mastodon.social/@user/123456789"
    
    posts = _parse_posts([mock_toot])
    assert len(posts) == 1
    post = posts[0]
    
    assert post["id"] == "123456789"
    assert post["platform"] == "mastodon"
    assert post["author_username"] == "user@mastodon.social"
    assert post["author_name"] == "User Name"
    # Basic HTML strip check
    assert post["text"] == "Hello world"
    assert post["likes"] == 100
    assert post["reposts"] == 20
    assert post["replies"] == 5
    # Engagement calculation should be identical to Bluesky/X: (100 likes * 2) + (20 reposts * 3) + 5 replies = 265
    assert post["engagement_score"] == 265
    assert post["url"] == "https://mastodon.social/@user/123456789"
    assert post["created_at"] == datetime(2023, 10, 1, 12, 0, tzinfo=timezone.utc)


@patch("fetch_mastodon.get_client")
def test_get_timeline_with_limit(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    # Generate 15 dummy toots
    dummy_toots = []
    for i in range(15):
        toot = MagicMock()
        toot.id = i
        toot.favourites_count = i
        toot.reblogs_count = 0
        toot.replies_count = 0
        toot.content = f"Post {i}"
        toot.created_at = datetime(2023, 10, 1, 12, i % 60, tzinfo=timezone.utc)
        toot.url = f"http://example.com/{i}"
        
        account = toot.account
        account.acct = f"user{i}"
        account.display_name = f"User {i}"
        dummy_toots.append(toot)
    
    # Mock timeline_home to return all 15
    mock_client.timeline_home.return_value = dummy_toots
    
    posts = get_timeline(limit=10)
    
    # It should only return 10 items because we passed `limit=10`
    assert len(posts) == 10
    mock_client.timeline_home.assert_called_once_with(limit=40)

@patch("fetch_mastodon.get_client")
def test_get_timeline_with_time_window(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    now = datetime(2023, 10, 2, 12, 0, tzinfo=timezone.utc)
    
    # One post 1 hour ago (within 24h)
    toot1 = MagicMock(id=1, favourites_count=0, reblogs_count=0, replies_count=0, content="Inside", url="u1")
    toot1.created_at = datetime(2023, 10, 2, 11, 0, tzinfo=timezone.utc)
    toot1.account.acct = "user1"
    
    # One post 48 hours ago (outside 24h)
    toot2 = MagicMock(id=2, favourites_count=0, reblogs_count=0, replies_count=0, content="Outside", url="u2")
    toot2.created_at = datetime(2023, 9, 30, 12, 0, tzinfo=timezone.utc)
    toot2.account.acct = "user2"
    
    mock_client.timeline_home.return_value = [toot1, toot2]

    with patch('fetch_mastodon.datetime') as mock_datetime:
        mock_datetime.now.return_value = now
        # We need to ensure timedelta and other parts work too, but often easier to just mock the subtraction result or the cutoff calculation
        # However, datetime.now() is what we used.
        posts = get_timeline(hours=24)
        
    assert len(posts) == 1
    assert posts[0]["text"] == "Inside"

