"""
fetch_timeline.py
Fetches all posts from the authenticated user's home timeline
for the past 24 hours using the X API v2.
"""

import os
import tweepy
from datetime import datetime, timezone, timedelta


def get_client() -> tweepy.Client:
    """Build and return an authenticated Tweepy v2 Client."""
    return tweepy.Client(
        bearer_token=os.environ["X_BEARER_TOKEN"],
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
        wait_on_rate_limit=True,
    )


def fetch_timeline(client: tweepy.Client, hours: int = 24, limit: int | None = None) -> list[dict]:
    """
    Fetch posts from the home timeline. 
    By default, fetches posts from the past `hours` hours (filtered by start_time).
    If `limit` is provided, fetches exactly that many of the latest posts instead.
    Returns a list of post dicts sorted by time (newest first).
    """
    start_time = None
    max_results = 100
    
    if limit is not None:
        print(f"[fetch] Fetching last {limit} posts...")
        max_results = min(limit, 100)
    else:
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        print(f"[fetch] Fetching posts since {start_time.isoformat()} ...")

    posts = []
    pagination_token = None

    while True:
        # If we have a limit and we've reached it, stop.
        if limit is not None and len(posts) >= limit:
            break

        fetch_count = max_results
        if limit is not None:
            fetch_count = min(max_results, limit - len(posts))
            if fetch_count <= 0:
                break

        response = client.get_home_timeline(
            start_time=start_time,
            max_results=fetch_count,
            pagination_token=pagination_token,
            tweet_fields=[
                "created_at",
                "public_metrics",
                "author_id",
                "text",
                "entities",
            ],
            expansions=["author_id"],
            user_fields=["name", "username"],
        )

        if not response.data:
            break

        # Build author lookup from includes
        authors = {}
        if response.includes and "users" in response.includes:
            for user in response.includes["users"]:
                authors[user.id] = {
                    "name": user.name,
                    "username": user.username,
                }

        for tweet in response.data:
            author = authors.get(tweet.author_id, {"name": "Unknown", "username": "unknown"})
            metrics = tweet.public_metrics or {}
            posts.append({
                "id": tweet.id,
                "text": tweet.text,
                "created_at": tweet.created_at,
                "author_name": author["name"],
                "author_username": author["username"],
                "likes": metrics.get("like_count", 0),
                "retweets": metrics.get("retweet_count", 0),
                "replies": metrics.get("reply_count", 0),
                "url": f"https://x.com/{author['username']}/status/{tweet.id}",
            })

        # Check for next page
        meta = response.meta or {}
        pagination_token = meta.get("next_token")
        if not pagination_token:
            break

    print(f"[fetch] Retrieved {len(posts)} posts.")
    # Sort newest first
    posts.sort(key=lambda p: p["created_at"], reverse=True)
    return posts
