"""
fetchers/bluesky_fetcher.py
BlueskyFetcher — fetches the authenticated user's Following timeline via atproto SDK.
"""

import os
from datetime import datetime, timezone, timedelta
from atproto import Client, models

from scoring import calculate_engagement_score, add_z_scores
from fetchers.base import BasePlatformFetcher

_REQUIRED_ENV_VARS = ["BSKY_HANDLE", "BSKY_APP_PASSWORD"]


class BlueskyFetcher(BasePlatformFetcher):
    """Fetches posts from the Bluesky Following timeline."""

    platform_name = "bluesky"

    # ------------------------------------------------------------------ #
    # ABC contract                                                         #
    # ------------------------------------------------------------------ #

    def is_configured(self) -> bool:
        """Return True if all Bluesky env vars are present."""
        return all(os.environ.get(k) for k in _REQUIRED_ENV_VARS)

    def fetch_posts(self, hours: int = 24, limit: int | None = None) -> list[dict]:
        """
        Authenticate with Bluesky and fetch posts from the Following timeline.
        By default fetches posts from the past `hours` hours.
        If `limit` is provided, fetches exactly that many recent posts.
        """
        client = self._get_client()
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        if limit is not None:
            print(f"[fetch-bluesky] Fetching last {limit} posts...")
        else:
            print(f"[fetch-bluesky] Fetching posts since {cutoff_time.isoformat()}...")

        feed_views = self._fetch_all_feeds(client, cutoff_time, limit)
        posts = self._parse_posts(feed_views)

        # Filter / truncate
        if limit is None:
            posts = [p for p in posts if p["created_at"] >= cutoff_time]
        elif len(posts) > limit:
            posts = posts[:limit]

        add_z_scores(posts)
        print(f"[fetch-bluesky] Retrieved {len(posts)} posts.")
        posts.sort(key=lambda p: p["created_at"], reverse=True)
        return posts

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _get_client(self) -> Client:
        """Build and return an authenticated atproto Client."""
        handle = os.environ.get("BSKY_HANDLE")
        password = os.environ.get("BSKY_APP_PASSWORD")
        if not handle or not password:
            raise ValueError("Missing BSKY_HANDLE or BSKY_APP_PASSWORD in environment.")
        client = Client()
        client.login(handle, password)
        return client

    def _parse_posts(self, feed_views: list) -> list[dict]:
        """Transform atproto feed views into the standard Post dictionary list."""
        parsed = []
        seen_uris: set = set()

        for feed_view in feed_views:
            post = feed_view.post

            # Deduplicate (feed sometimes returns the same post as a repost)
            if post.uri in seen_uris:
                continue
            seen_uris.add(post.uri)

            rkey = post.uri.split('/')[-1]
            author_handle = post.author.handle
            url = f"https://bsky.app/profile/{author_handle}/post/{rkey}"

            likes = getattr(post, 'like_count', 0)
            reposts = getattr(post, 'repost_count', 0)
            replies = getattr(post, 'reply_count', 0)

            record = post.record
            try:
                created_at_str = (getattr(record, 'created_at', None)
                                  or getattr(record, 'createdAt', ''))
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

    def _fetch_all_feeds(self, client: Client, cutoff_time: datetime, limit: int | None) -> list:
        """Fetch pages from the timeline until cutoff or limit is reached."""
        params = models.AppBskyFeedGetTimeline.Params(limit=100)
        response = client.app.bsky.feed.get_timeline(params)
        feed_views = response.feed

        while getattr(response, 'cursor', None):
            if limit is not None and len(feed_views) >= limit:
                break

            if limit is None and feed_views:
                last_view = feed_views[-1]
                try:
                    created_at_str = (getattr(last_view.post.record, 'created_at', None)
                                      or getattr(last_view.post.record, 'createdAt', ''))
                    last_time = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    if last_time < cutoff_time:
                        break
                except (ValueError, AttributeError):
                    pass

            params = models.AppBskyFeedGetTimeline.Params(limit=100, cursor=response.cursor)
            response = client.app.bsky.feed.get_timeline(params)
            feed_views.extend(response.feed)

        return feed_views
