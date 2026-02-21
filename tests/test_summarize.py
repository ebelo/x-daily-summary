import pytest
from datetime import datetime, timezone
from summarize import build_markdown, _get_sort_score

def test_get_sort_score():
    post1 = {"engagement_score": 38, "normalized_score": 0.5}
    assert _get_sort_score(post1) == pytest.approx(0.5)
    post2 = {"engagement_score": 38}
    assert _get_sort_score(post2) == pytest.approx(38.0)

def test_build_markdown_empty():
    md = build_markdown([])
    assert "No posts found" in md
    assert "0 posts" in md

def test_build_markdown_sorting():
    posts = [
        {
            "platform": "x",
            "author_username": "low_engager",
            "author_name": "Low",
            "text": "Hello",
            "created_at": datetime.now(timezone.utc),
            "likes": 0, "reposts": 0, "replies": 0,
            "engagement_score": 0,
            "url": "https://x.com/1"
        },
        {
            "platform": "x",
            "author_username": "high_engager",
            "author_name": "High",
            "text": "Viral!",
            "created_at": datetime.now(timezone.utc),
            "likes": 1000, "reposts": 500, "replies": 100,
            "engagement_score": 3600,
            "url": "https://x.com/2"
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
            "platform": "x",
            "author_username": "user1",
            "author_name": "User One",
            "text": "Post A",
            "created_at": datetime.now(timezone.utc),
            "likes": 0, "reposts": 0, "replies": 0,
            "engagement_score": 0,
            "url": "https://x.com/a"
        },
        {
            "platform": "bluesky",
            "author_username": "user1",
            "author_name": "User One",
            "text": "Post B",
            "created_at": datetime.now(timezone.utc),
            "likes": 0, "reposts": 0, "replies": 0,
            "engagement_score": 0,
            "url": "https://x.com/b"
        }
    ]
    md = build_markdown(posts)
    # user1 from x and user1 from bluesky should be separated because of platform grouping
    assert md.count("## [x] @user1") == 1
    assert md.count("## [bluesky] @user1") == 1
    assert "Post A" in md
    assert "Post B" in md
