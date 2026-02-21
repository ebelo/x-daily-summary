"""
fetch_bluesky.py
Fetches the user's Following timeline using the official atproto SDK.
"""

import os
from datetime import datetime, timezone
from atproto import Client, models
from scoring import calculate_engagement_score, add_z_scores


def get_client() -> Client:
    """Build and return an authenticated atproto Client."""
    client = Client()
    handle = os.environ.get("BSKY_HANDLE")
    password = os.environ.get("BSKY_APP_PASSWORD")
    if not handle or not password:
        raise ValueError("Missing BSKY_HANDLE or BSKY_APP_PASSWORD in environment.")
    client.login(handle, password)
    return client


def _parse_posts(feed_views: list) -> list[dict]:
    """Transform atproto feed views into the standard Post dictionary list."""
    parsed = []
    seen_uris = set()
    
    for feed_view in feed_views:
        post = feed_view.post
        
        # Deduplicate (sometimes feed returns the same post as a repost)
        if post.uri in seen_uris:
            continue
        seen_uris.add(post.uri)
        
        # Extract the rkey from the uri (at://did:plc:.../app.bsky.feed.post/<rkey>)
        rkey = post.uri.split('/')[-1]
        author_handle = post.author.handle
        url = f"https://bsky.app/profile/{author_handle}/post/{rkey}"
        
        likes = getattr(post, 'like_count', 0)
        reposts = getattr(post, 'repost_count', 0)
        replies = getattr(post, 'reply_count', 0)
        
        record = post.record
        try:
            # record.created_at is a string like '2023-09-06T12:34:56.789Z'
            created_at_str = getattr(record, 'created_at', None) or getattr(record, 'createdAt', '')
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError, TypeError):
            created_at = datetime.now(timezone.utc)
            
        parsed.append({
            "id": post.uri,
            "platform": "bluesky",
            "text": getattr(record, 'text', ''),
            "created_at": created_at,
            "author_name": post.author.display_name or author_handle,
            "author_username": author_handle,
            "likes": likes,
            "reposts": reposts,
            "replies": replies,
            "engagement_score": calculate_engagement_score(likes, reposts, replies),
            "url": url,
        })
    return parsed





def get_timeline(limit: int | None = None) -> list[dict]:
    """
    Fetch posts from the home timeline.
    Returns a list of standard Post dicts.
    """
    client = get_client()
    
    if limit is None:
        limit = 100
        
    print(f"[fetch-bluesky] Fetching {limit} posts...")
    
    response = client.app.bsky.feed.get_timeline(models.AppBskyFeedGetTimeline.Params(limit=min(limit, 100)))
    feed_views = response.feed
    
    # If we need more than 100, we could paginate, but limiting to 100 per call for simplicity
    while len(feed_views) < limit and getattr(response, 'cursor', None):
        remaining = limit - len(feed_views)
        response = client.app.bsky.feed.get_timeline(models.AppBskyFeedGetTimeline.Params(limit=min(remaining, 100), cursor=response.cursor))
        feed_views.extend(response.feed)
        
    posts = _parse_posts(feed_views)
    add_z_scores(posts)
    
    print(f"[fetch-bluesky] Retrieved {len(posts)} posts.")
    posts.sort(key=lambda p: p["created_at"], reverse=True)
    return posts
