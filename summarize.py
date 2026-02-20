"""
summarize.py
Takes a list of post dicts and produces a markdown daily digest string.
Posts are grouped by author, sorted by engagement.
"""

from datetime import datetime, timezone


FIRE_THRESHOLD = 100   # likes to earn the 🔥 emoji


def _engagement_score(post: dict) -> int:
    return post["likes"] * 2 + post["retweets"] * 3 + post["replies"]


def build_markdown(posts: list[dict], generated_at: datetime | None = None) -> str:
    """
    Build a markdown summary string from a list of post dicts.
    """
    if generated_at is None:
        generated_at = datetime.now(timezone.utc)

    date_str = generated_at.strftime("%A, %B %d %Y")
    time_str = generated_at.strftime("%H:%M UTC")
    total = len(posts)

    lines = [
        f"# 🐦 X Daily Summary — {date_str}",
        f"",
        f"> Generated at **{time_str}** · **{total} posts** from the past 24 hours",
        f"",
        "---",
        "",
    ]

    if not posts:
        lines.append("_No posts found in the past 24 hours._")
        return "\n".join(lines)

    # Group by author
    by_author: dict[str, list[dict]] = {}
    for post in posts:
        key = post["author_username"]
        by_author.setdefault(key, []).append(post)

    # Sort authors by their total engagement
    def author_score(username: str) -> int:
        return sum(_engagement_score(p) for p in by_author[username])

    sorted_authors = sorted(by_author.keys(), key=author_score, reverse=True)

    # Table of contents
    lines.append("## 📋 Authors in This Summary")
    lines.append("")
    for username in sorted_authors:
        author_posts = by_author[username]
        name = author_posts[0]["author_name"]
        count = len(author_posts)
        top_likes = max(p["likes"] for p in author_posts)
        fire = " 🔥" if top_likes >= FIRE_THRESHOLD else ""
        lines.append(f"- **{name}** (@{username}){fire} — {count} post{'s' if count > 1 else ''}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Per-author sections
    for username in sorted_authors:
        author_posts = by_author[username]
        name = author_posts[0]["author_name"]

        # Sort posts by engagement within this author
        author_posts_sorted = sorted(author_posts, key=_engagement_score, reverse=True)

        lines.append(f"## @{username} — {name}")
        lines.append("")

        for post in author_posts_sorted:
            ts = post["created_at"]
            if hasattr(ts, "strftime"):
                ts_str = ts.strftime("%H:%M UTC")
            else:
                ts_str = str(ts)

            fire = " 🔥" if post["likes"] >= FIRE_THRESHOLD else ""
            stats = (
                f"❤️ {post['likes']:,}  "
                f"🔁 {post['retweets']:,}  "
                f"💬 {post['replies']:,}"
            )

            # Wrap tweet text in blockquote, handle newlines
            quoted_text = "\n> ".join(post["text"].splitlines())

            lines.append(f"> {quoted_text}")
            lines.append(f">")
            lines.append(f"> {stats}{fire}  ·  🕐 {ts_str}  ·  [View post]({post['url']})")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)
