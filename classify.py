"""
classify.py
Map-reduce helpers for the local-model intel report pipeline.

Pipeline:
  1. parse_posts_from_markdown()   - extract posts from summary .md
  2. classify_post()               - assign each post to a category (1 model call)
  3. select_top_per_category()     - pick top N by engagement per category
"""

import re
from typing import Callable

CATEGORIES = [
    "Geopolitics & Security",
    "Economics & Markets",
    "AI & Technology",
    "Health & Science",
    "Sports & Performance",
    "Society & Culture",
]

CATEGORY_PROMPT = f"""Classify the following social media post into exactly ONE of these categories:
{chr(10).join(f'- {c}' for c in CATEGORIES)}

Reply with ONLY the category name, nothing else.

POST:
"""

BATCH_PROMPT = f"""Classify the following 10 social media posts into exactly ONE of these categories:
{chr(10).join(f'- {c}' for c in CATEGORIES)}

Respond with a simple numbered list in the format:
1. [Category Name]
2. [Category Name]
... (up to 10)

POSTS:
"""


def _process_post_block(block: list[str], author: str, engagement_match: re.Match, engagement_re: re.Pattern) -> dict | None:
    """Helper to process an accumulated block of lines into a post dict."""
    if not author or not block:
        return None
        
    engagement = int(engagement_match.group(1).replace(",", ""))
    text = " ".join(
        l for l in block
        if not engagement_re.search(l) and not l.startswith("❤")
    ).strip()
    
    if text:
        return {
            "text": text,
            "engagement": engagement,
            "author": author,
        }
    return None


def parse_posts_from_markdown(markdown: str) -> list[dict]:
    """
    Extract individual posts from a summary markdown file.

    Returns a list of dicts:
        {{"text": str, "engagement": int, "author": str}}

    Posts are ranked by engagement in the summary, so the order is preserved.
    """
    posts = []
    current_author = ""

    # Match author headers (with optional platform tag): ## [x] @username — Display Name
    author_re = re.compile(r"^## (?:\[.*?\] )?@(\S+)")
    # Match engagement lines: > ❤️ 1,234  🔁 ...
    engagement_re = re.compile(r"❤️\s*([\d,]+)")

    current_block: list[str] = []

    for line in markdown.splitlines():
        author_match = author_re.match(line)
        if author_match:
            current_author = author_match.group(1)
            current_block.clear()
            continue

        if line.startswith("> ") or line == ">":
            current_block.append(line.lstrip("> ").strip())
            # Check if this line has the engagement marker — signals end of one post
            eng_match = engagement_re.search(line)
            if eng_match:
                post = _process_post_block(current_block, current_author, eng_match, engagement_re)
                if post:
                    posts.append(post)
                current_block.clear()
        else:
            current_block.clear()

    return posts



def classify_batch(texts: list[str], call_fn: Callable[[str], str]) -> list[str | None]:
    """
    Classify a batch of up to 10 posts in a single model call.

    Returns a list of category names (one per input text), or None for failures.
    """
    if not texts:
        return []

    # Build the batch prompt
    batch_text = "\n".join(f"{i + 1}. {text}" for i, text in enumerate(texts))
    prompt = BATCH_PROMPT + batch_text

    response = call_fn(prompt).strip().lower()
    results: list[str | None] = [None] * len(texts)

    # Parse numbered list: 1. Category, 2. Category...
    # We look for lines starting with "N." or "N)"
    lines = response.splitlines()
    for line in lines:
        match = re.search(r"^(\d+)[.)]\s*(.*)", line.strip())
        if match:
            idx = int(match.group(1)) - 1
            if 0 <= idx < len(texts):
                raw_cat = match.group(2).strip()
                # Use the same matching logic as single classification
                results[idx] = _match_category(raw_cat)

    return results


def _match_category(raw_cat: str) -> str | None:
    """Helper to match a raw model response to a valid category name."""
    raw_cat = raw_cat.lower()
    # First: try exact match
    for cat in CATEGORIES:
        if cat.lower() in raw_cat:
            return cat
    # Second: try keyword match
    for cat in CATEGORIES:
        words = [w for w in cat.lower().split() if w not in ("&", "and")]
        if any(w in raw_cat for w in words):
            return cat
    return None


def classify_post(text: str, call_fn: Callable[[str], str]) -> str | None:
    """
    Classify a single post into one of the CATEGORIES.
    """
    prompt = CATEGORY_PROMPT + text
    response = call_fn(prompt).strip().lower()
    return _match_category(response)


def select_top_per_category(
    posts: list[dict],
    top_n: int = 10,
) -> dict[str, list[dict]]:
    """
    Group classified posts by category and select the top N by engagement.

    Each post dict must have a "category" key (added by the caller after classification).

    Returns:
        {category_name: [top_n posts sorted by engagement desc]}
    """
    grouped: dict[str, list[dict]] = {cat: [] for cat in CATEGORIES}

    for post in posts:
        cat = post.get("category")
        if cat not in grouped:
            continue  # skip posts without a valid category
        grouped[cat].append(post)

    # Sort each group by engagement and take top N
    return {
        cat: sorted(posts_in_cat, key=lambda p: p["engagement"], reverse=True)[:top_n]
        for cat, posts_in_cat in grouped.items()
        if posts_in_cat  # omit empty categories
    }
