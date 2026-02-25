# Agent Documentation: Social Intelligence Suite

This document provides architectural context, data models, and coding standards for agents working on the Social Intelligence Suite.

## Pipeline Architecture

The application is a single-direction CLI pipeline categorized into five stages:

1.  **Extraction**: `fetch_timeline.py` (X via Tweepy), `fetch_bluesky.py` (Bluesky via atproto), and `fetch_mastodon.py` (Mastodon via Mastodon.py) fetch raw posts.
2.  **Scoring**: `scoring.py` calculates an `engagement_score` and adds a `normalized_score` (Z-Score) for fair cross-platform ranking.
3.  **Synthesis (Summary)**: `summarize.py` aggregates posts into a structured Markdown digest.
4.  **Intelligence**: `intel_report.py` (supported by `classify.py`) parses the digest and synthesizes a strategic "Global Situation Report".
5.  **Orchestration**: `main.py` is the entry point that manages the state, configuration, and flow between modules.

### Entry Points
- `main.py`: Primary CLI tool for fetching and report generation.
- `run_daily.py`: Wrapper for automated daily execution (cron/task scheduler).

---

## Data Model: Standard Post Schema

All modules in the pipeline must consume and produce the following dictionary schema for a single post:

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | `str` | Platform-specific unique identifier. |
| `platform` | `str` | Either `'x'`, `'bluesky'`, or `'mastodon'`. |
| `text` | `str` | Raw text content of the post. |
| `created_at` | `datetime` | UTC timestamp of post creation. |
| `author_name` | `str` | Display name of the author. |
| `author_username`| `str` | Handle/Username (e.g., `elonmusk`). |
| `likes` | `int` | Raw like/heart count. |
| `reposts` | `int` | Raw repost/retweet count. |
| `replies` | `int` | Raw reply count. |
| `engagement_score`| `int` | Weighted score: `(likes*2) + (reposts*3) + replies`. |
| `url` | `str` | Permanent direct link to the post. |

### Dynamic Fields
- `normalized_score`: Added by `scoring.add_z_scores()` (float).
- `category`: Added by `classify.py` during intelligence processing (string).

---

## Environment Configuration

The tool uses `.env` for secrets. Different modes require different subsets of variables:

### 1. Platform Source Credentials
- **X (Twitter)**: `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`, `X_BEARER_TOKEN`.
- **Bluesky**: `BSKY_HANDLE`, `BSKY_APP_PASSWORD`.
- **Mastodon**: `MASTODON_CLIENT_ID`, `MASTODON_CLIENT_SECRET`, `MASTODON_ACCESS_TOKEN`, `MASTODON_API_BASE_URL`.

### 2. AI Intelligence Backends
- **Gemini**: `GEMINI_API_KEY`, `GEMINI_MODEL`.
- **Ollama**: `INTEL_BACKEND=ollama`, `OLLAMA_MODEL`, `OLLAMA_URL`.

---

## CLI Reference

- `python main.py --source all --limit 20`: Fetches the latest 20 posts from X, Bluesky, and Mastodon (ignoring 24h default).
- `python main.py --from-summary`: Reprocesses today's existing summary without calling APIs.
- `python main.py --intel-limit 50`: Caps the posts sent to the AI at 50 (ranked by engagement).
- `python main.py --intel-backend ollama`: Forces the local model execution regardless of `.env` configuration.

---

## AI Backend Configuration

### Gemini Backend (Cloud)
- **Strategy**: Single-shot generation.
- **Logic**: Sends the (optionally truncated) summary to `gemini-flash-latest`.
- **Retries**: Uses `tenacity` with exponential backoff for `RESOURCE_EXHAUSTED` errors.

### Ollama Backend (Local)
- **Strategy**: Map-Reduce pipeline to handle context limits.
- **Phases**:
    1.  **Map**: Classify posts in batches of 10.
    2.  **Select**: Pick top 15 posts per category by engagement.
    3.  **Draft**: Generate briefings for each of the 6 categories.
    4.  **Reduce**: Synthesize a 1-paragraph Executive Summary.

---

## Standard: Code Style & Error Handling

- **Naming**: Use private function prefixes (`_`) for module-specific logic (e.g., `_load_env`, `_parse_tweets`).
- **Constants**: Use `UPPER_CASE` for module-level constants (e.g., `CATEGORIES`, `FIRE_THRESHOLD`).
- **Type Hints**: Use Python 3.10+ syntax (e.g., `str | None`, `list[dict]`).
- **Startup Validation**: Use `sys.exit(1)` with a descriptive error message if critical environment variables/files are missing.
- **API Call Failures**: Return string error prefixes (e.g., `"Error: ..."`) from API synthesis wrappers instead of raising naked exceptions.
- **Retry Logic**: Use the `tenacity` decorator on cloud API calls with exponential backoff for rate limits (e.g., `RESOURCE_EXHAUSTED`).
- **Credential Validation**: Use conditional feature detection in the orchestrator (`has_x`, `has_bsky`) but hard failure inside the specific fetch modules (`ValueError`).
- **Module Prefixes**: Use `[module-name]` prefixes in print statements (e.g., `[fetch-x]`, `[intel]`).

---

## Standard: Testing & Mocking

- **Organization**: All tests reside in the `tests/` directory and match the source file name (e.g., `tests/test_scoring.py`).
- **Mocking Strategy**: 
    - Use `@patch` decorators for function-level mocking.
    - Use `MagicMock` for complex API clients (Tweepy/atproto).
    - Use `pytest.approx()` for all floating-point assertions (normalized scores).
- **Credentials**: Use explicit `"DUMMY_..."` values for mock secrets to satisfy security scanners.
- **Sys Path**: Insert the project root into `sys.path[0]` at the top of test files to allow direct module imports.

---

## Standard: Scoring & Ranking

- **Engagement Formula**: `(likes * 2) + (reposts * 3) + replies`.
- **Normalization**: Z-Score calculation standardizes metrics across networks with different activity levels.
- **Heat indicators**: Posts exceeding 100 likes (`FIRE_THRESHOLD`) should be marked with a fire emoji (`🔥`) in summaries.
- **Sort Priority**: Global ranking is performed by `normalized_score` first, falling back to raw `engagement_score`.

---

## Standard: Intelligence Classification

The system uses a fixed taxonomy of 6 categories defined in `classify.py`:
1. `Geopolitics & Security`
2. `Economics & Markets`
3. `AI & Technology`
4. `Health & Science`
5. `Sports & Performance`
6. `Society & Culture`

- **Matching**: Classification must use exact string matching against this list before any fallback.
- **Batching**: Always classify posts in batches of 10 to minimize LLM inference overhead.

---

## Standard: Git & CI/CD Workflow

- **Branching**: For each semantically coherent change, create a specifically named feature branch (e.g., `feat/json-data-contract`). Avoid committing directly to `main`.
- **Pull Requests**: Prepare a proper Pull Request (PR) with a descriptive summary of the changes before merging to `main`.
- **SonarCloud Analysis**: Pushing commits to a branch triggers automated SonarCloud analysis (available via the PR checks or SonarCloud dashboard).
- **Zero Feedback Tolerance**: You must update your code continuously until SonarCloud reports zero issues or warnings. 
- **Commented Code False Positives**: *Attention:* Sometimes SonarCloud misidentifies dense descriptive or mathematical text as "commented out code". Do not just delete the comment; rewrite it to be strictly textual and narrative so SonarCloud recognizes it as documentation.
