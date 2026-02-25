"""
main.py
Entry point for the X daily summary tool.
Loads credentials, fetches the past 24 hours of posts, and writes a markdown file.

Usage:
  python main.py                          # Full 24h fetch + intel report
  python main.py --limit 100             # Fetch only last 100 posts
  python main.py --intel-limit 200       # Cap posts sent to AI at top 200
  python main.py --from-summary          # Skip X API, re-use today's summary file
  python main.py --from-summary summaries/summary_2026-02-20.md  # Use specific file
"""

import os
import sys
import argparse
import re
import json
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from summarize import build_markdown
from intel_report import generate_intel_report


def _ensure_utf8_stdout() -> None:
    """Reconfigure stdout to UTF-8 on Windows (avoids cp1252 UnicodeEncodeError)."""
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")


def _load_env(env_path: Path) -> None:
    """Load .env credentials."""
    if not env_path.exists():
        print("[error] .env file not found.")
        print("  → Copy .env.example to .env and fill in your credentials.")
        sys.exit(1)
    load_dotenv(dotenv_path=env_path)


def _process_truncate_section(section_lines: list[str], current_total: int, limit: int) -> tuple[str, int]:
    """Helper to process a section's posts and truncate them to fit the limit."""
    post_end_indices = [i for i, l in enumerate(section_lines) if "[View post](" in l]
    
    if not post_end_indices:
        return "", 0
        
    current_section = [section_lines[0]]  # Add ## @author line
    last_e = 1
    posts_added = 0
    
    for e in post_end_indices:
        if current_total + posts_added >= limit:
            break
        current_section.append("\n".join(section_lines[last_e:e+1]))
        posts_added += 1
        last_e = e + 1
        
    if posts_added > 0:
        return "\n".join(current_section), posts_added
    return "", 0


def _truncate_markdown(markdown: str, intel_limit: int) -> str:
    """
    Limit the markdown sent to the AI to the top N posts by engagement.
    Preserves the header section and truncates at the post level.
    Posts are identified by the '> ❤️' engagement line in the markdown.
    """
    lines = markdown.splitlines()

    # Find where per-author sections begin (lines starting with ## @)
    section_indices = [i for i, l in enumerate(lines) if l.startswith("## @")]

    if not section_indices or intel_limit <= 0:
        return markdown

    header = "\n".join(lines[:section_indices[0]])
    kept_sections = []
    total = 0

    for idx, start in enumerate(section_indices):
        if total >= intel_limit:
            break
            
        end = section_indices[idx + 1] if idx + 1 < len(section_indices) else len(lines)
        section_str, posts_added = _process_truncate_section(lines[start:end], total, intel_limit)
        
        if posts_added > 0:
            kept_sections.append(section_str)
            total += posts_added

    print(f"[intel] Truncated to ~{total} posts (limit: {intel_limit})", flush=True)
    return header + "\n\n" + "\n\n".join(kept_sections)


def _parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Fetch and summarize X home timeline.")
    parser.add_argument(
        "--limit", "-l",
        type=int,
        help="Fetch only the last N posts instead of the past 24 hours."
    )
    parser.add_argument(
        "--source",
        type=str,
        choices=["x", "bluesky", "mastodon", "all"],
        default="all",
        help="Specific data source to scrape. Use 'all' to fetch and merge multiple available sources."
    )
    parser.add_argument(
        "--intel-limit",
        type=int,
        default=0,
        help="Cap the number of posts sent to the AI at N (by engagement order). "
             "Useful for local models with small context windows. 0 = no limit."
    )
    parser.add_argument(
        "--intel-backend",
        type=str,
        choices=["gemini", "ollama"],
        help="The intelligence backend to use (overrides INTEL_BACKEND env var)."
    )
    parser.add_argument(
        "--from-cache", "--from-summary",
        dest="from_cache",
        nargs="?",
        const="",          # --from-cache with no path → auto-detect today's file
        metavar="FILE",
        help="Skip API fetch and re-use existing JSON cache file. Pass a path, or omit for today's file."
    )
    return parser.parse_args()


def _load_existing_cache(from_cache_arg: str, output_dir: Path, now: datetime) -> tuple[str, list[dict]]:
    """Load an existing JSON cache file and its companion markdown summary."""
    if from_cache_arg:
        json_path = Path(from_cache_arg)
        if json_path.suffix == ".md":
            json_path = json_path.with_name(json_path.name.replace("summary_", "posts_").replace(".md", ".json"))
    else:
        # Auto-detect today's file
        json_path = output_dir / f"posts_{now.strftime('%Y-%m-%d')}.json"

    if not json_path.exists():
        print(f"[error] JSON cache file not found: {json_path}")
        sys.exit(1)

    with json_path.open("r", encoding="utf-8") as f:
        posts = json.load(f)

    # Load companion markdown if needed for backwards compatibility downstream (optional)
    md_path = json_path.with_name(json_path.name.replace("posts_", "summary_").replace(".json", ".md"))
    markdown = md_path.read_text(encoding="utf-8") if md_path.exists() else ""

    print(f"[skip] Loaded existing cache -> {json_path} ({len(posts)} posts)")
    return markdown, posts


def _run_fetch_and_summarize(args, env_path: Path, output_dir: Path, now: datetime) -> tuple[str, list[dict]]:
    """Fetch posts from configured sources and build a summary markdown."""
    _load_env(env_path)
    posts = []
    has_x = all(os.environ.get(k) for k in [
        "X_API_KEY", "X_API_SECRET",
        "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET", "X_BEARER_TOKEN"
    ])
    
    has_bsky = all(os.environ.get(k) for k in [
        "BSKY_HANDLE", "BSKY_APP_PASSWORD"
    ])
    
    has_mastodon = all(os.environ.get(k) for k in [
        "MASTODON_CLIENT_ID", "MASTODON_CLIENT_SECRET",
        "MASTODON_ACCESS_TOKEN", "MASTODON_API_BASE_URL"
    ])
    
    if args.source in ["all", "x"] and has_x:
        from fetch_timeline import get_client, fetch_timeline
        client = get_client()
        x_posts = fetch_timeline(client, hours=24, limit=args.limit)
        posts.extend(x_posts)
        
    if args.source in ["all", "bluesky"] and has_bsky:
        import fetch_bluesky
        bsky_posts = fetch_bluesky.get_timeline(hours=24, limit=args.limit)
        posts.extend(bsky_posts)
        
    if args.source in ["all", "mastodon"] and has_mastodon:
        import fetch_mastodon
        mastodon_posts = fetch_mastodon.get_timeline(hours=24, limit=args.limit)
        posts.extend(mastodon_posts)
        
    if not posts:
        print(f"[error] No posts fetched. Verify your credentials in .env. Attempted fetching for source: {args.source}")
        sys.exit(1)

    markdown = build_markdown(posts, generated_at=now)

    date_str = now.strftime('%Y-%m-%d')
    output_path = output_dir / f"summary_{date_str}.md"
    output_path.write_text(markdown, encoding="utf-8")
    
    json_path = output_dir / f"posts_{date_str}.json"
    json_path.write_text(json.dumps(posts, indent=2, default=str), encoding="utf-8")

    print(f"[done] Summary saved → {output_path}")
    print(f"[done] JSON cache saved → {json_path}")
    return markdown, posts


def _generate_and_save_intel_report(posts: list[dict], now: datetime, output_dir: Path, intel_limit: int, intel_backend: str | None = None):
    """Generate the AI intelligence report and save it to disk."""
    posts_to_analyze = posts[:intel_limit] if intel_limit > 0 else posts

    if intel_backend:
        os.environ["INTEL_BACKEND"] = intel_backend

    backend = os.getenv("INTEL_BACKEND", "gemini")
    model = (os.getenv("OLLAMA_MODEL", "") if backend == "ollama" 
             else os.getenv("GEMINI_MODEL", "gemini-flash-latest"))
    print(f"[intel] Generating report for {len(posts_to_analyze)} posts (backend={backend}, model={model or 'default'})...")

    intel_md = generate_intel_report(posts_to_analyze)

    intel_filename = f"intel_report_{now.strftime('%Y-%m-%d')}.md"
    intel_path = output_dir / intel_filename
    intel_path.write_text(intel_md, encoding="utf-8")
    print(f"[done] Intel report saved -> {intel_path}")


def main():
    _ensure_utf8_stdout()
    args = _parse_args()

    env_path = Path(__file__).parent / ".env"
    
    # Always load the environment to ensure API keys (like Gemini/Ollama URLs) are available
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)

    output_dir = Path(__file__).parent / "summaries"
    output_dir.mkdir(exist_ok=True)
    now = datetime.now(timezone.utc)

    if args.from_cache is not None:
        _, posts = _load_existing_cache(args.from_cache, output_dir, now)
    else:
        _, posts = _run_fetch_and_summarize(args, env_path, output_dir, now)

    _generate_and_save_intel_report(posts, now, output_dir, args.intel_limit, getattr(args, "intel_backend", None))


if __name__ == "__main__":
    main()
