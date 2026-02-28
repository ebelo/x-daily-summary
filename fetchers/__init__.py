"""
fetchers/__init__.py
Public API for the fetchers package.
"""

from fetchers.base import BasePlatformFetcher
from fetchers.x_fetcher import XFetcher
from fetchers.bluesky_fetcher import BlueskyFetcher
from fetchers.mastodon_fetcher import MastodonFetcher

__all__ = [
    "BasePlatformFetcher",
    "XFetcher",
    "BlueskyFetcher",
    "MastodonFetcher",
]
