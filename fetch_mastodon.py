"""
fetch_mastodon.py
Backward-compatible wrapper — delegates to fetchers.MastodonFetcher.
New code should use `from fetchers import MastodonFetcher` directly.
"""

from mastodon import Mastodon
from fetchers.mastodon_fetcher import MastodonFetcher

_fetcher = MastodonFetcher()


def get_client() -> Mastodon:
    """Return an authenticated Mastodon client."""
    return _fetcher._get_client()


def get_timeline(hours: int = 24, limit: int | None = None) -> list[dict]:
    """
    Fetch posts from the Mastodon home timeline.
    Kept for backward compatibility — delegates to MastodonFetcher.fetch_posts().
    """
    return _fetcher.fetch_posts(hours=hours, limit=limit)
