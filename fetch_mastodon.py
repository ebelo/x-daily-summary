"""
fetch_mastodon.py
Fetches the user's home timeline using the official Mastodon.py SDK.
"""

import os
from datetime import datetime
from mastodon import Mastodon
from scoring import calculate_engagement_score, add_z_scores


def get_client() -> Mastodon:
    """Build and return an authenticated Mastodon Client."""
    client_id = os.environ.get("MASTODON_CLIENT_ID")
    client_secret = os.environ.get("MASTODON_CLIENT_SECRET")
    access_token = os.environ.get("MASTODON_ACCESS_TOKEN")
    api_base_url = os.environ.get("MASTODON_API_BASE_URL")
    
    if not client_id or not client_secret or not access_token or not api_base_url:
        raise ValueError("Missing MASTODON_CLIENT_ID, MASTODON_CLIENT_SECRET, MASTODON_ACCESS_TOKEN, or MASTODON_API_BASE_URL in environment.")
        
    return Mastodon(
        client_id=client_id,
        client_secret=client_secret,
        access_token=access_token,
        api_base_url=api_base_url
    )


def _parse_posts(toots: list) -> list[dict]:
    """Transform Mastodon API toots into the standard Post dictionary list."""
    parsed = []
    
    for toot in toots:
        account = toot.account
        
        # Engagement metrics
        likes = toot.favourites_count
        reposts = toot.reblogs_count
        replies = toot.replies_count
        
        # created_at is a datetime object in Mastodon.py
        created_at = toot.created_at
        
        # Fallback to local username if no display_name
        author_name = account.display_name if account.display_name else account.username
        author_username = account.acct  # This includes @domain if it's from another instance

        # Extract text from HTML (Mastodon content is HTML by default)
        # Using a simple regex to strip basic tags for the intel report text representation
        import re
        content_text = re.sub('<[^<]+?>', '', toot.content)
        
        # Mastodon standard URL scheme vs the URI internal ID
        # toot.url points directly to the web view
        url = toot.url

        parsed.append({
            "id": str(toot.id),
            "platform": "mastodon",
            "text": content_text.strip(),
            "created_at": created_at,
            "author_name": author_name,
            "author_username": author_username,
            "likes": likes,
            "reposts": reposts,
            "replies": replies,
            "engagement_score": calculate_engagement_score(likes, reposts, replies),
            "url": url,
        })
    return parsed


def _fetch_all_toots(client: Mastodon, cutoff_time: datetime, limit: int | None) -> list:
    """Helper to fetch toots until cutoff or limit is reached."""
    toots = []
    batch = client.timeline_home(limit=40)
    
    while batch:
        for toot in batch:
            if limit is not None and len(toots) >= limit:
                return toots
            if limit is None and toot.created_at < cutoff_time:
                return toots
            toots.append(toot)
            
        if limit is None and batch[-1].created_at < cutoff_time:
            break
            
        batch = client.fetch_next(batch)
    return toots


def get_timeline(hours: int = 24, limit: int | None = None) -> list[dict]:
    """
    Fetch posts from the home timeline.
    By default, fetches posts from the past `hours` hours.
    If `limit` is provided, fetches exactly that many of the latest posts instead.
    Returns a list of standard Post dicts.
    """
    from datetime import timezone, timedelta
    client = get_client()
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    if limit is not None:
        print(f"[fetch-mastodon] Fetching last {limit} posts...")
    else:
        print(f"[fetch-mastodon] Fetching posts since {cutoff_time.isoformat()}...")
    
    toots = _fetch_all_toots(client, cutoff_time, limit)
    
    posts = _parse_posts(toots)
    add_z_scores(posts)
    
    print(f"[fetch-mastodon] Retrieved {len(posts)} posts.")
    posts.sort(key=lambda p: p["created_at"], reverse=True)
    return posts
