import pytest
from datetime import datetime, timezone
from summarize import build_markdown, _engagement_score

def test_engagement_score():
    post = {"likes": 10, "retweets": 5, "replies": 3}
    # likes*2 + retweets*3 + replies = 10*2 + 5*3 + 3 = 20 + 15 + 3 = 38
    assert _engagement_score(post) == 38

def test_build_markdown_empty():
    md = build_markdown([])
    assert "No posts found" in md
    assert "0 posts" in md

def test_build_markdown_sorting():
    posts = [
        {
            "author_username": "low_engager",
            "author_name": "Low",
            "text": "Hello",
            "created_at": datetime.now(timezone.utc),
            "likes": 0, "retweets": 0, "replies": 0,
            "url": "http://x.com/1"
        },
        {
            "author_username": "high_engager",
            "author_name": "High",
            "text": "Viral!",
            "created_at": datetime.now(timezone.utc),
            "likes": 1000, "retweets": 500, "replies": 100,
            "url": "http://x.com/2"
        }
    ]
    md = build_markdown(posts)
    
    # High engager should appear before low engager in the authors list
    high_pos = md.find("@high_engager")
    low_pos = md.find("@low_engager")
    assert high_pos < low_pos
    assert "🔥" in md  # 1000 likes should trigger fire emoji

def test_build_markdown_grouping():
    posts = [
        {
            "author_username": "user1",
            "author_name": "User One",
            "text": "Post A",
            "created_at": datetime.now(timezone.utc),
            "likes": 0, "retweets": 0, "replies": 0,
            "url": "http://x.com/a"
        },
        {
            "author_username": "user1",
            "author_name": "User One",
            "text": "Post B",
            "created_at": datetime.now(timezone.utc),
            "likes": 0, "retweets": 0, "replies": 0,
            "url": "http://x.com/b"
        }
    ]
    md = build_markdown(posts)
    # user1 should only have one section header
    assert md.count("## @user1") == 1
    assert "Post A" in md
    assert "Post B" in md
