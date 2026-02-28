"""
fetch_bluesky.py
Backward-compatible wrapper — delegates to fetchers.BlueskyFetcher.
New code should use `from fetchers import BlueskyFetcher` directly.
"""

from atproto import Client
from fetchers.bluesky_fetcher import BlueskyFetcher

_fetcher = BlueskyFetcher()


def get_client() -> Client:
    """Return an authenticated atproto Client."""
    return _fetcher._get_client()


def get_timeline(hours: int = 24, limit: int | None = None) -> list[dict]:
    """
    Fetch posts from the Bluesky Following timeline.
    Kept for backward compatibility — delegates to BlueskyFetcher.fetch_posts().
    """
    return _fetcher.fetch_posts(hours=hours, limit=limit)
