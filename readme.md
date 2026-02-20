# X Daily Summary Tool

A local Python tool that fetches your X (Twitter) home timeline, ranks posts by engagement,
and generates two files:

- **`summary_YYYY-MM-DD.md`** — Chronological digest grouped by author, ranked by engagement.
- **`intel_report_YYYY-MM-DD.md`** — Strategic AI briefing synthesized by Gemini (Global Situation Report format).

---

## 🛠️ Environment & Requirements

| Requirement | Detail |
|---|---|
| **OS** | Windows (preferred), Linux or macOS also supported |
| **Python** | 3.10 or higher |
| **Git** | Required to clone and push to the repository |
| **X API Tier** | Basic Tier ($100/mo) — needed for `home_timeline` access |
| **Gemini API Key** | Free tier available at [ai.google.dev](https://ai.google.dev) |

---

## 🚀 Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up credentials:**
   ```bash
   cp .env.example .env
   # Fill in your X API credentials and GEMINI_API_KEY / Ollama settings
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
| *(none)* | Full run: fetch 24h of posts, build summary, generate intel report |
| `--limit N` | Fetch only the last N posts (saves X API cost during testing) |
| `--intel-limit N` | Send only the top N posts to the AI. Uses precise intra-section truncation to guarantee exactly N posts are evaluated. |
| `--from-summary [FILE]` | Skip the X API fetch entirely — re-use today's (or a specified) summary file to regenerate the intel report |

**Examples:**
```bash
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
> The Gemini Intelligence Layer uses **Gemini 1.5 Flash** within free-tier quotas where available.

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
| `OLLAMA_MODEL` | e.g. `mistral` (default) |
| `OLLAMA_URL` | `http://localhost:11434/api/generate` (default) |

**Ollama setup (one-time):**
1. Download & install [Ollama](https://ollama.com/download).
2. Pull a model: `ollama pull mistral`
3. Set `INTEL_BACKEND=ollama` in your `.env`.
4. Run the script as usual — no API key or internet required.

> **Recommended local model**: `mistral` (~4GB) — best balance of speed and prompt adherence for the Map-Reduce pipeline.

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
| `fetch_timeline.py` | X API fetching logic |
| `summarize.py` | Engagement ranking and markdown formatting |
| `intel_report.py` | Gemini AI synthesis layer |
| `run_daily.ps1` | Windows Task Scheduler automation script |
| `requirements.txt` | Python package dependencies |
| `.env.example` | Template for API credentials |
| `tests/` | Automated unit and mock tests |
| `summaries/` | Local output folder (Git-ignored) |

---

## ⏰ Automating with Task Scheduler (Windows)

1. Open **Task Scheduler** → *Create Basic Task*
2. Name: `X Daily Summary`
3. Trigger: **Daily** at your preferred time (e.g. 07:00)
4. Action: **Start a Program**
   - Program: `powershell.exe`
   - Arguments: `-ExecutionPolicy Bypass -File "C:\path\to\x_daily_summary\run_daily.ps1"`
5. Save → Done ✅

---

## 💻 Tested Hardware

The local Ollama backend was successfully tested on the following setup:

| Component | Detail |
|---|---|
| **Machine** | Lenovo ThinkPad P14s (`20VX0068MZ`) |
| **CPU** | Intel Core i7-1165G7 @ 2.80GHz (4 cores / 8 threads) |
| **RAM** | 16 GB |
| **GPU** | NVIDIA T500 — 4 GB VRAM (CUDA 12.8, Driver 573.57) |
| **OS** | Windows 11, 64-bit |

**GPU usage confirmed:** Ollama automatically uses **hybrid CPU+GPU inference** (split offloading). With Mistral 7B (~4.4GB), approximately **2.7 GB of model layers are loaded into GPU VRAM**, with the remainder running on CPU RAM. `nvidia-smi` confirmed `ollama.exe` was the active GPU process during inference.

**Generation speed:** ~10–15 tokens/sec for a typical 10–100 post summary.

---

GitHub Repository: https://github.com/ebelo/x-daily-summary
