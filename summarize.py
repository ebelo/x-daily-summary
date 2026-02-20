"""
summarize.py
Takes a list of post dicts and produces a markdown daily digest string.
Posts are grouped by author, sorted by engagement.
"""

from datetime import datetime, timezone


FIRE_THRESHOLD = 100   # likes to earn the 🔥 emoji


def _engagement_score(post: dict) -> int:
    return post["likes"] * 2 + post["retweets"] * 3 + post["replies"]


def _group_by_author(posts: list[dict]) -> dict[str, list[dict]]:
    """Group posts by their author username."""
    by_author: dict[str, list[dict]] = {}
    for post in posts:
        key = post["author_username"]
        by_author.setdefault(key, []).append(post)
    return by_author


def _format_author_list(lines: list[str], sorted_authors: list[str], by_author: dict):
    """Append the authors table of contents to the lines list."""
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


def _format_author_section(lines: list[str], username: str, author_posts: list[dict]):
    """Append a single author's section with their posts to the lines list."""
    name = author_posts[0]["author_name"]
    # Sort posts by engagement within this author
    sorted_posts = sorted(author_posts, key=_engagement_score, reverse=True)

    lines.append(f"## @{username} — {name}")
    lines.append("")

    for post in sorted_posts:
        ts = post["created_at"]
        ts_str = ts.strftime("%H:%M UTC") if hasattr(ts, "strftime") else str(ts)
        fire = " 🔥" if post["likes"] >= FIRE_THRESHOLD else ""
        stats = f"❤️ {post['likes']:,}  🔁 {post['retweets']:,}  💬 {post['replies']:,}"
        quoted_text = "\n> ".join(post["text"].splitlines())

        lines.append(f"> {quoted_text}")
        lines.append(">")
        lines.append(f"> {stats}{fire}  ·  🕐 {ts_str}  ·  [View post]({post['url']})")
        lines.append("")

    lines.append("---")
    lines.append("")


def build_markdown(posts: list[dict], generated_at: datetime | None = None) -> str:
    """Build a markdown summary string from a list of post dicts."""
    if generated_at is None:
        generated_at = datetime.now(timezone.utc)

    total = len(posts)
    lines = [
        f"# 🐦 X Daily Summary — {generated_at.strftime('%A, %B %d %Y')}",
        "",
        f"> Generated at **{generated_at.strftime('%H:%M UTC')}** · **{total} posts** from the past 24 hours",
        "",
        "---",
        "",
    ]

    if not posts:
        lines.append("_No posts found in the past 24 hours._")
        return "\n".join(lines)

    by_author = _group_by_author(posts)
    sorted_authors = sorted(by_author.keys(), 
                            key=lambda u: sum(_engagement_score(p) for p in by_author[u]), 
                            reverse=True)

    _format_author_list(lines, sorted_authors, by_author)

    for username in sorted_authors:
        _format_author_section(lines, username, by_author[username])

    return "\n".join(lines)
