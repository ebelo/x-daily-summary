"""
fetchers/x_fetcher.py
XFetcher — fetches the authenticated user's home timeline via X API v2 (tweepy).
"""

import os
import tweepy
from datetime import datetime, timezone, timedelta

from scoring import calculate_engagement_score, add_z_scores
from fetchers.base import BasePlatformFetcher

_REQUIRED_ENV_VARS = [
    "X_API_KEY", "X_API_SECRET",
    "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET",
    "X_BEARER_TOKEN",
]


class XFetcher(BasePlatformFetcher):
    """Fetches posts from the X (Twitter) home timeline."""

    platform_name = "x"

    # ------------------------------------------------------------------ #
    # ABC contract                                                         #
    # ------------------------------------------------------------------ #

    def is_configured(self) -> bool:
        """Return True if all X API env vars are present."""
        return all(os.environ.get(k) for k in _REQUIRED_ENV_VARS)

    def fetch_posts(self, hours: int = 24, limit: int | None = None) -> list[dict]:
        """
        Authenticate with X and fetch posts from the home timeline.
        By default fetches posts from the past `hours` hours.
        If `limit` is provided, fetches exactly that many recent posts.
        """
        client = self._get_client()
        return self._fetch_timeline(client, hours=hours, limit=limit)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _get_client(self) -> tweepy.Client:
        """Build and return an authenticated Tweepy v2 Client."""
        return tweepy.Client(
            bearer_token=os.environ["X_BEARER_TOKEN"],
            consumer_key=os.environ["X_API_KEY"],
            consumer_secret=os.environ["X_API_SECRET"],
            access_token=os.environ["X_ACCESS_TOKEN"],
            access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
            wait_on_rate_limit=True,
        )

    def _prepare_fetch_params(self, hours: int, limit: int | None) -> tuple[datetime | None, int]:
        """Determine start_time and max_results based on limit and hours."""
        if limit is not None:
            print(f"[fetch-x] Fetching last {limit} posts...")
            return None, min(limit, 100)

        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        print(f"[fetch-x] Fetching posts since {start_time.isoformat()} ...")
        return start_time, 100

    def _extract_authors(self, response: tweepy.Response) -> dict:
        """Extract author information from API response includes."""
        authors = {}
        if response.includes and "users" in response.includes:
            for user in response.includes["users"]:
                authors[user.id] = {
                    "name": user.name,
                    "username": user.username,
                }
        return authors

    def _parse_tweets(self, tweets: list, authors: dict) -> list[dict]:
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
                "engagement_score": calculate_engagement_score(
                    metrics.get("like_count", 0),
                    metrics.get("retweet_count", 0),
                    metrics.get("reply_count", 0)
                ),
                "url": f"https://x.com/{author['username']}/status/{tweet.id}",
            })
        return parsed

    def _fetch_timeline(
        self,
        client: tweepy.Client,
        hours: int = 24,
        limit: int | None = None,
    ) -> list[dict]:
        """
        Core pagination loop. Returns posts sorted newest-first with z-scores.
        """
        start_time, max_results = self._prepare_fetch_params(hours, limit)
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

            authors = self._extract_authors(response)
            posts.extend(self._parse_tweets(response.data, authors))

            pagination_token = (response.meta or {}).get("next_token")
            if not pagination_token:
                break

        print(f"[fetch-x] Retrieved {len(posts)} posts.")
        add_z_scores(posts)
        posts.sort(key=lambda p: p["created_at"], reverse=True)
        return posts
