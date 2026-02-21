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
        choices=["x", "bluesky", "all"],
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
        "--from-summary",
        nargs="?",
        const="",          # --from-summary with no path → auto-detect today's file
        metavar="FILE",
        help="Skip X API fetch and re-use an existing summary file. "
             "Pass a path, or omit for today's auto-detected file."
    )
    return parser.parse_args()


def _load_existing_summary(from_summary_arg: str, output_dir: Path, now: datetime) -> str:
    """Load an existing summary file from disk."""
    if from_summary_arg:
        summary_path = Path(from_summary_arg)
    else:
        # Auto-detect today's file
        summary_path = output_dir / f"summary_{now.strftime('%Y-%m-%d')}.md"

    if not summary_path.exists():
        print(f"[error] Summary file not found: {summary_path}")
        sys.exit(1)

    markdown = summary_path.read_text(encoding="utf-8")
    print(f"[skip] Loaded existing summary -> {summary_path}")
    return markdown


def _run_fetch_and_summarize(args, env_path: Path, output_dir: Path, now: datetime) -> str:
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
    
    if args.source in ["all", "x"] and has_x:
        from fetch_timeline import get_client, fetch_timeline
        client = get_client()
        x_posts = fetch_timeline(client, hours=24, limit=args.limit)
        posts.extend(x_posts)
        
    if args.source in ["all", "bluesky"] and has_bsky:
        import fetch_bluesky
        bsky_posts = fetch_bluesky.get_timeline(limit=args.limit)
        posts.extend(bsky_posts)
        
    if not posts:
        print(f"[error] No posts fetched. Verify your credentials in .env. Attempted fetching for source: {args.source}")
        sys.exit(1)

    markdown = build_markdown(posts, generated_at=now)

    filename = f"summary_{now.strftime('%Y-%m-%d')}.md"
    output_path = output_dir / filename
    output_path.write_text(markdown, encoding="utf-8")
    print(f"[done] Summary saved → {output_path}")
    return markdown


def _generate_and_save_intel_report(markdown: str, now: datetime, output_dir: Path, intel_limit: int):
    """Generate the AI intelligence report and save it to disk."""
    intel_input = markdown
    if intel_limit and intel_limit > 0:
        intel_input = _truncate_markdown(markdown, intel_limit)

    backend = os.getenv("INTEL_BACKEND", "gemini")
    model = (os.getenv("OLLAMA_MODEL", "") if backend == "ollama" 
             else os.getenv("GEMINI_MODEL", "gemini-flash-latest"))
    print(f"[intel] Generating report (backend={backend}, model={model or 'default'})...")

    intel_md = generate_intel_report(intel_input)

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

    if args.from_summary is not None:
        markdown = _load_existing_summary(args.from_summary, output_dir, now)
    else:
        markdown = _run_fetch_and_summarize(args, env_path, output_dir, now)

    _generate_and_save_intel_report(markdown, now, output_dir, args.intel_limit)


if __name__ == "__main__":
    main()
