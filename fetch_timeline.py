"""
fetch_timeline.py
Backward-compatible wrapper — delegates to fetchers.XFetcher.
New code should use `from fetchers import XFetcher` directly.
"""

import tweepy
from fetchers.x_fetcher import XFetcher

_fetcher = XFetcher()


def get_client() -> tweepy.Client:
    """Return an authenticated Tweepy v2 Client."""
    return _fetcher._get_client()


def fetch_timeline(client: tweepy.Client, hours: int = 24, limit: int | None = None) -> list[dict]:
    """
    Fetch posts from the X home timeline.
    Kept for backward compatibility — delegates to XFetcher._fetch_timeline().
    """
    return _fetcher._fetch_timeline(client, hours=hours, limit=limit)
