---
name: Platform Integration
description: When the agent needs to add a new social media data source or API platform to the suite.
---

## Purpose

Guides the process of wiring a new social media platform or data source into the existing extraction pipeline and normalizing its data.

## When to Use

Activate when adding a new fetcher module, integrating a new social network API, or modifying the multi-source aggregation logic in `main.py`.

## Instructions

- Create a new module (e.g., `fetch_newsource.py`) to interact with the target API.
- Implement a `get_client()` function to authenticate using environment variables. Hardcode fallback error behavior (e.g., raise `ValueError` on missing credentials).
- Implement a `get_timeline(limit: int)` function that fetches posts and parses them into the standard pipeline dictionary schema.
- Ensure every post dict includes a strict `platform` identifier string (e.g., `x` or `bluesky`).
- Update `main.py` credential checks to feature-detect the new integration via `os.environ.get()` (e.g., `has_newsource`).
- Expand the `--source` CLI argument choices in `_parse_args()` to include the new platform.
- Wire the new fetcher into `_run_fetch_and_summarize()` to append its results to the global `posts` list.
- Verify that `scoring.add_z_scores()` accommodates the new platform's volume naturally (the Z-score handles disparate volume natively).
- Ensure the markdown generator (`summarize.py`) correctly groups authors using the composite tag template (`[platform] @username`).
