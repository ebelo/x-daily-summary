import pytest
from fetch_timeline import fetch_timeline
from unittest.mock import MagicMock

def test_fetch_timeline_with_limit(mocker):
    # Mock Tweepy Client
    mock_client = MagicMock()
    
    # Mock response data
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
    
    # Call fetch_timeline with a limit of 1
    posts = fetch_timeline(mock_client, limit=1)
    
    assert len(posts) == 1
    assert posts[0]["author_username"] == "test_user"
    assert posts[0]["text"] == "Mock post"
    
    # Ensure get_home_timeline was called with max_results=1
    mock_client.get_home_timeline.assert_called_once()
    _, kwargs = mock_client.get_home_timeline.call_args
    assert kwargs["max_results"] == 1

def test_fetch_timeline_pagination(mocker):
    mock_client = MagicMock()
    
    # Page 1
    mock_tweet1 = MagicMock(id=1, text="T1", author_id=456, public_metrics={}, created_at="2026-02-20T09:00:00Z")
    mock_response1 = MagicMock(data=[mock_tweet1], includes={"users": []}, meta={"next_token": "token2"})
    
    # Page 2
    mock_tweet2 = MagicMock(id=2, text="T2", author_id=456, public_metrics={}, created_at="2026-02-20T08:00:00Z")
    mock_response2 = MagicMock(data=[mock_tweet2], includes={"users": []}, meta={"next_token": None})
    
    mock_client.get_home_timeline.side_effect = [mock_response1, mock_response2]
    
    # Fetch with limit 2
    posts = fetch_timeline(mock_client, limit=2)
    
    assert len(posts) == 2
    assert mock_client.get_home_timeline.call_count == 2
