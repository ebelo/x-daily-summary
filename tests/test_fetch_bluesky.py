import pytest
import os
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from fetch_bluesky import get_client, _parse_posts, _add_z_scores, get_timeline

def test_get_client_success():
    with patch.dict(os.environ, {"BSKY_HANDLE": "user.bsky.social", "BSKY_APP_PASSWORD": "DUMMY_BSKY_PASSWORD"}):
        with patch("fetch_bluesky.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            client = get_client()
            assert client == mock_client
            mock_client.login.assert_called_once_with("user.bsky.social", "DUMMY_BSKY_PASSWORD")

def test_get_client_missing_env():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="Missing BSKY_HANDLE or BSKY_APP_PASSWORD"):
            get_client()

def test_parse_posts():
    mock_feed_view = MagicMock()
    mock_post = mock_feed_view.post
    mock_post.uri = "at://did:plc:123/app.bsky.feed.post/3k6xx"
    mock_post.author.handle = "user.bsky.social"
    mock_post.author.display_name = "User"
    mock_post.like_count = 100
    mock_post.repost_count = 20
    mock_post.reply_count = 5
    
    mock_record = mock_post.record
    mock_record.text = "Hello world"
    mock_record.created_at = "2023-10-01T12:00:00Z"
    
    posts = _parse_posts([mock_feed_view])
    assert len(posts) == 1
    post = posts[0]
    
    assert post["id"] == "at://did:plc:123/app.bsky.feed.post/3k6xx"
    assert post["platform"] == "bluesky"
    assert post["author_username"] == "user.bsky.social"
    assert post["author_name"] == "User"
    assert post["text"] == "Hello world"
    assert post["likes"] == 100
    assert post["reposts"] == 20
    assert post["replies"] == 5
    # Engagement calculation: (100 likes * 2) + (20 reposts * 3) + 5 replies = 265
    assert post["engagement_score"] == 265
    assert post["url"] == "https://bsky.app/profile/user.bsky.social/post/3k6xx"
    assert post["created_at"] == datetime(2023, 10, 1, 12, 0, tzinfo=timezone.utc)

def test_add_z_scores():
    posts = [
        {"engagement_score": 10},
        {"engagement_score": 20},
        {"engagement_score": 30},
    ]
    _add_z_scores(posts)
    # Mean is 20, std dev is ~8.16
    assert posts[0]["normalized_score"] < 0
    assert posts[1]["normalized_score"] == pytest.approx(0.0)
    assert posts[2]["normalized_score"] > 0
    
def test_add_z_scores_zero_variance():
    posts = [
        {"engagement_score": 10},
        {"engagement_score": 10},
    ]
    _add_z_scores(posts)
    assert posts[0]["normalized_score"] == pytest.approx(0.0)
    assert posts[1]["normalized_score"] == pytest.approx(0.0)

@patch("fetch_bluesky.get_client")
def test_get_timeline(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.feed = []
    mock_response.cursor = None
    mock_client.app.bsky.feed.get_timeline.return_value = mock_response
    
    posts = get_timeline(limit=10)
    assert posts == []
    mock_client.app.bsky.feed.get_timeline.assert_called_once()
