"""
main.py
Entry point for the X daily summary tool.
Loads credentials, fetches the past 24 hours of posts, and writes a markdown file.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fetch_timeline import get_client, fetch_timeline
from summarize import build_markdown


def main():
    # ------------------------------------------------------------------ #
    # 1. Load credentials from .env
    # ------------------------------------------------------------------ #
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print("[error] .env file not found.")
        print("  → Copy .env.example to .env and fill in your X API credentials.")
        sys.exit(1)

    load_dotenv(dotenv_path=env_path)

    required = [
        "X_API_KEY",
        "X_API_SECRET",
        "X_ACCESS_TOKEN",
        "X_ACCESS_TOKEN_SECRET",
        "X_BEARER_TOKEN",
    ]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"[error] Missing environment variables: {', '.join(missing)}")
        sys.exit(1)

    # ------------------------------------------------------------------ #
    # 2. Fetch timeline
    # ------------------------------------------------------------------ #
    client = get_client()
    posts = fetch_timeline(client, hours=24)

    # ------------------------------------------------------------------ #
    # 3. Build markdown
    # ------------------------------------------------------------------ #
    now = datetime.now(timezone.utc)
    markdown = build_markdown(posts, generated_at=now)

    # ------------------------------------------------------------------ #
    # 4. Save to summaries/summary_YYYY-MM-DD.md
    # ------------------------------------------------------------------ #
    output_dir = Path(__file__).parent / "summaries"
    output_dir.mkdir(exist_ok=True)

    filename = f"summary_{now.strftime('%Y-%m-%d')}.md"
    output_path = output_dir / filename

    output_path.write_text(markdown, encoding="utf-8")
    print(f"[done] Summary saved -> {output_path}")


if __name__ == "__main__":
    main()
