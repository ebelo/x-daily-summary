# X Daily Summary Tool

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Social feeds — X (Twitter), Bluesky, Mastodon — are high-signal, high-noise environments. Following the right people means your feed can surface critical geopolitical developments, market moves, and technology shifts — but extracting that signal requires scrolling, context-switching, and sustained attention across dozens of threads.

This tool replaces that process with a single daily document. It reads your feed, ranks posts by engagement, and uses a Large Language Model (LLM) to synthesize everything into a **strategic intelligence report** — structured by theme, stripped of noise, and ready to read in minutes.

The goal is simple: **the important information, without the cognitive overhead.**

Currently implemented for **X (Twitter)**, **Bluesky**, and **Mastodon** natively. Extending to other feeds (like Reddit or RSS) is a [priority contribution area](CONTRIBUTING.md).

It generates two files:
- **`summary_YYYY-MM-DD.md`** — Full ranked digest of the past 24 hours of posts, merged from all active sources, grouped by platform and author.
- **`intel_report_YYYY-MM-DD.md`** — AI-written intelligence brief (Global Situation Report format), covering geopolitics, markets, technology, health, and more.

Two AI backends are supported — a cloud model (Gemini) or a fully local model (Ollama) that runs on your own hardware at no cost.


---

## 🧐 Alternatives & Philosophy

There are many existing Twitter summarization tools (e.g., *TwitterSummary, News-Digest, X Copilot, Scholar*). Most of these alternative solutions rely on the exact same architecture as each other: they scrape specific tweets, send them to a cloud API like OpenAI or Claude, and deliver the result via a web UI, a Chrome extension, or a Slack bot.

**X Daily Summary Tool** was built for a different use case: **information consumers who value privacy and deep focus.**

1. **Local Privacy:** Optimized for 100% local, offline AI inference (Ollama + Llama 3.2). No third party ever sees your feed, your reading habits, or your API keys.
2. **Deep Reading:** No web dashboard or chatbot interface. Generates a raw Markdown file on your hard drive, designed for undistracted reading. Treats your feed like a serious daily intelligence briefing.
3. **Algorithmic Independence:** Fetches the raw, chronological feeds — bypassing platform ranking algorithms — and applies its own transparent, cross-platform Z-Score normalization before feeding it to the AI.
4. **Multi-Source Architecture:** The pipeline (fetch → normalize → synthesize) seamlessly merges data from disparate platforms into a single standardized Data Contract. X, Bluesky, and Mastodon are today's implementations; Reddit and RSS are natural next steps.

---

## 🛠️ Environment & Requirements

| Requirement | Detail |
|---|---|
| **OS** | Windows, macOS, or Linux |
| **Python** | 3.10 or higher |
| **Git** | Required to clone and push to the repository |
| **X API Access** | (Optional) Developer account with API credits. Apply at [developer.x.com](https://developer.x.com) |
| **Bluesky Access** | (Optional) Generate an App Password in your Bluesky Privacy settings. |
| **Mastodon Access** | (Optional) Generate an Access Token in your Mastodon instance's Development settings. |
| **AI Backend** | Gemini API key (cloud) **or** [Ollama](https://ollama.com) installed locally — pick one |

---

## 🚀 Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up credentials:**
   ```bash
   cp .env.example .env
   # Fill in your platform API credentials and Gemini/Ollama settings
   ```

3. **Run the full 24-hour summary:**
   ```bash
   python main.py
   ```

4. **Check `summaries/`** for two output files:
   - `summary_YYYY-MM-DD.md` — raw ranked digest
   - `intel_report_YYYY-MM-DD.md` — AI-synthesized strategic briefing

---

## 🖥️ CLI Reference

| Flag | Description |
|---|---|
| *(none)* | Full run: fetch the last 24h of posts from all configured platforms, build summary, generate intel report |
| `--source [x\|bluesky\|mastodon]` | Fetch from a specific platform only (e.g. `--source mastodon`) |
| `--limit N` | Fetch exactly N latest posts per platform, bypassing the 24h time window (saves API quotas during testing) |
| `--intel-limit N` | Send only the top N posts to the AI. Uses precise intra-section truncation to guarantee exactly N posts are evaluated. |
| `--from-summary [FILE]` | Skip all API fetches entirely — re-use today's (or a specified) summary file to regenerate the intel report |

**Examples:**
```bash
# Fetch only from Bluesky
python main.py --source bluesky

# Test with 10 posts to avoid API costs
python main.py --limit 10

# Regenerate intel report from today's existing summary (no X API call)
python main.py --from-summary

# Regenerate intel report from a specific date's summary
python main.py --from-summary summaries/summary_2026-02-19.md

# Use a local model with context limit
python main.py --from-summary --intel-limit 150
```

## 💰 Cost-Saving Test Mode

Use `--limit` to fetch only a small number of posts (no 24h window):
```bash
python main.py --limit 10
```
> As of February 2026, fetching ~800 tweets costs roughly **$4 USD** via X API Basic Tier.
> The Gemini Intelligence Layer uses **Gemini Flash** within free-tier quotas where available. Local Ollama inference is completely free.

---

## 🤖 Intelligence Layer (Dual-Strategy Architecture)

The tool supports two distinct backends for generating the strategic briefing, configurable via `INTEL_BACKEND` in your `.env`. Because local models and cloud models have vastly different capabilities, we built a bespoke strategy for each:

### Option A: Gemini (Cloud Strategy)

- **How it works:** Single-pass synthesis. The entire day's raw markdown (800+ posts) is sent to Gemini in one massive API call.
- **Why:** Gemini 1.5 Flash has a 1M+ token context window and high reasoning capability, allowing it to easily read the entire timeline at once and synthesize complex thematic sections.

| Key | Value |
|---|---|
| `INTEL_BACKEND` | `gemini` |
| `GEMINI_API_KEY` | Your key from [ai.google.dev](https://ai.google.dev) |
| `GEMINI_MODEL` | e.g. `gemini-flash-latest` (default) |

### Option B: Ollama (Local Map-Reduce Strategy)

- **How it works:** A multi-step map-reduce pipeline.
  1. **Map (Batching):** Parses the raw markdown and sends batches of 10 posts to Ollama to be strictly *classified* into 6 categories.
  2. **Filter:** Selects the top 10 posts per category by engagement.
  3. **Reduce:** Makes 6 separate calls to Ollama, asking it to write a short thematic section for each category using only the top posts.
- **Why:** Local models like `mistral` have limited context windows (4k-8k tokens) and can hallucinate if fed too much disconnected information at once. Batch classification provides a ~10x speedup over single-post classification, making local inference practical.

| Key | Value |
|---|---|
| `INTEL_BACKEND` | `ollama` |
| `OLLAMA_MODEL` | e.g. `llama3.2:latest` (recommended) |
| `OLLAMA_URL` | `http://localhost:11434/api/generate` (default) |
| `OLLAMA_TOP_PER_CATEGORY` | Number of top posts per category to synthesize (default: `10`) |

**Ollama setup (Windows & macOS):**
1. Download & install [Ollama](https://ollama.com/download).
2. Open terminal and pull a model: `ollama pull llama3.2`
3. Set `INTEL_BACKEND=ollama` and `OLLAMA_MODEL=llama3.2:latest` in your `.env`.
4. Run the python script as usual — no API key or internet required.

**Ollama setup (Ubuntu & WSL Native):**
1. Install Ollama natively: `curl -fsSL https://ollama.com/install.sh | sh`
2. Start the daemon (if not already running): `nohup ollama serve > ollama.log 2>&1 &`
3. Pull a model: `ollama run llama3.2:latest` (type `/bye` to exit when done)
4. Create a virtual environment and run the project completely inside Linux.

> **Recommended local model**: `llama3.2:latest` (2GB) — fits entirely in 4GB VRAM, processes 839 posts in ~25 minutes. Mistral 7B (4.4GB) also works but is significantly slower due to RAM spill on hardware with ≤4GB VRAM.

---

## 🧪 Running Tests

Automated tests verify logic without spending API credits:
```bash
pytest
```

---

## 📂 Files

| File | Purpose |
|---|---|
| `main.py` | Orchestrator and entry point |
| `fetch_timeline.py` | X (Twitter) API fetching logic (last 24h by default) |
| `fetch_bluesky.py` | Bluesky (atproto) fetching logic (last 24h by default) |
| `fetch_mastodon.py` | Mastodon API fetching logic (last 24h by default) |
| `summarize.py` | Engagement ranking, Z-Score normalization, and markdown formatting |
| `intel_report.py` | AI synthesis layer (Gemini cloud + Ollama local Map-Reduce) |
| `run_daily.py` | Cross-platform daily runner (schedule with cron or Task Scheduler) |
| `requirements.txt` | Python package dependencies |
| `.env.example` | Template for API credentials |
| `tests/` | Automated unit and mock tests |
| `summaries/` | Local output folder (Git-ignored) |

---

## ⏰ Scheduling Daily Runs

`run_daily.py` is a cross-platform Python wrapper that calls `main.py` and reports the result.

**macOS / Linux (cron):**
```bash
# Run every day at 07:00
crontab -e
0 7 * * * /usr/bin/python3 /path/to/x_daily_summary/run_daily.py
```

**Windows (Task Scheduler):**
1. Open **Task Scheduler** → *Create Basic Task*
2. Trigger: **Daily** at your preferred time
3. Action: **Start a Program**
   - Program: `python.exe`
   - Arguments: `C:\path\to\x_daily_summary\run_daily.py`
4. Save → Done ✅

---

## 💻 Tested Hardware

The Ollama local backend was first tested on this setup:

| Component | Detail |
|---|---|
| **Machine** | Lenovo ThinkPad P14s (`20VX0068MZ`) |
| **CPU** | Intel Core i7-1165G7 @ 2.80GHz (4 cores / 8 threads) |
| **RAM** | 16 GB |
| **GPU** | NVIDIA T500 — 4 GB VRAM (CUDA 12.8, Driver 573.57) |
| **OS** | Windows 11, 64-bit |

**GPU usage confirmed:** With `llama3.2:latest` (2GB), the entire model fits in the T500's 4GB VRAM — no CPU RAM spill. `nvidia-smi` confirms `ollama.exe` as the active GPU process during inference. Ollama handles VRAM allocation automatically when switching models.

**Generation speed:** ~25 minutes for a full 839-post run with Llama 3.2 (3B). Mistral 7B takes significantly longer due to partial RAM spill on this hardware.

📊 **Running on different hardware?** Please contribute your benchmark results to [BENCHMARKS.md](BENCHMARKS.md) — just hardware specs, model name, post count, and timing.

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide. **Priority areas:**
- 🌐 New data sources (Reddit, RSS, Telegram)
- 🤖 Improving local LLM quality and performance
- ➕ New AI backends (Claude, OpenAI, LlamaCpp, Mistral API)
- 📊 Hardware benchmarks — add a row to [BENCHMARKS.md](BENCHMARKS.md)

This project is licensed under the [MIT License](LICENSE).

---

GitHub Repository: https://github.com/ebelo/x-daily-summary
