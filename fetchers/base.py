"""
fetchers/base.py
Abstract base class that all platform fetchers must implement.
"""

from abc import ABC, abstractmethod


class BasePlatformFetcher(ABC):
    """
    Contract every platform fetcher must satisfy.

    Subclasses must define:
      - platform_name (class attribute) — matches the --source CLI value
      - is_configured()  — True if required env vars are present
      - fetch_posts()    — authenticate and return the standardised post list
    """

    platform_name: str  # e.g. "x", "bluesky", "mastodon"

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if all required environment variables are present."""
        ...

    @abstractmethod
    def fetch_posts(self, hours: int = 24, limit: int | None = None) -> list[dict]:
        """
        Authenticate with the platform and fetch posts.

        Args:
            hours: Lookback window in hours (used when limit is None).
            limit: If set, fetch exactly this many recent posts instead.

        Returns:
            A list of standardised post dicts (id, platform, text, created_at,
            author_name, author_username, likes, reposts, replies,
            engagement_score, url).
        """
        ...
