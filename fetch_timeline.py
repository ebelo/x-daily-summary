"""
fetch_timeline.py
Fetches all posts from the authenticated user's home timeline
for the past 24 hours using the X API v2.
"""

import os
import math
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


def _prepare_fetch_params(hours: int, limit: int | None) -> tuple[datetime | None, int]:
    """Determine start_time and max_results based on limit and hours."""
    if limit is not None:
        print(f"[fetch] Fetching last {limit} posts...")
        return None, min(limit, 100)
    
    start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    print(f"[fetch] Fetching posts since {start_time.isoformat()} ...")
    return start_time, 100


def _extract_authors(response: tweepy.Response) -> dict:
    """Extract author information from API response includes."""
    authors = {}
    if response.includes and "users" in response.includes:
        for user in response.includes["users"]:
            authors[user.id] = {
                "name": user.name,
                "username": user.username,
            }
    return authors


def _parse_tweets(tweets: list, authors: dict) -> list[dict]:
    """Transform batch of tweets into list of dicts."""
    parsed = []
    for tweet in tweets:
        author = authors.get(tweet.author_id, {"name": "Unknown", "username": "unknown"})
        metrics = tweet.public_metrics or {}
        parsed.append({
            "id": tweet.id,
            "platform": "x",
            "text": tweet.text,
            "created_at": tweet.created_at,
            "author_name": author["name"],
            "author_username": author["username"],
            "likes": metrics.get("like_count", 0),
            "reposts": metrics.get("retweet_count", 0),
            "replies": metrics.get("reply_count", 0),
            "engagement_score": (metrics.get("like_count", 0) * 2) + (metrics.get("retweet_count", 0) * 3) + metrics.get("reply_count", 0),
            "url": f"https://x.com/{author['username']}/status/{tweet.id}",
        })
    return parsed


def _add_z_scores(posts: list[dict]) -> None:
    """Add a normalized_score (Z-Score) to each post in the list."""
    if not posts:
        return
        
    scores = [p['engagement_score'] for p in posts]
    mean = sum(scores) / len(scores)
    
    variance = sum((s - mean) ** 2 for s in scores) / len(scores)
    std_dev = math.sqrt(variance)
    
    for p in posts:
        if std_dev == 0:
            p['normalized_score'] = 0.0
        else:
            p['normalized_score'] = (p['engagement_score'] - mean) / std_dev


def fetch_timeline(client: tweepy.Client, hours: int = 24, limit: int | None = None) -> list[dict]:
    """
    Fetch posts from the home timeline. 
    By default, fetches posts from the past `hours` hours (filtered by start_time).
    If `limit` is provided, fetches exactly that many of the latest posts instead.
    Returns a list of post dicts sorted by time (newest first).
    """
    start_time, max_results = _prepare_fetch_params(hours, limit)
    posts = []
    pagination_token = None

    while True:
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
            tweet_fields=["created_at", "public_metrics", "author_id", "text", "entities"],
            expansions=["author_id"],
            user_fields=["name", "username"],
        )

        if not response.data:
            break

        authors = _extract_authors(response)
        posts.extend(_parse_tweets(response.data, authors))

        pagination_token = (response.meta or {}).get("next_token")
        if not pagination_token:
            break

    print(f"[fetch] Retrieved {len(posts)} posts.")
    
    _add_z_scores(posts)
    posts.sort(key=lambda p: p["created_at"], reverse=True)
    return posts
