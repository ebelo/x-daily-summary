X Daily Summary Tool
====================

A simple Python tool to fetch your X (Twitter) home timeline from the past 24 hours 
and generate a structured markdown summary.

## 🛠️ Environment & Requirements
- **OS**: Windows (preferred for the `.ps1` automation), but works on Linux/macOS.
- **Python**: 3.10+ recommended.
- **Git**: Required to push/sync changes.
- **X API Tier**: **Basic Tier ($100/mo)** is required to access the `home_timeline` endpoint.

## 🚀 Quick Start
1. Ensure Python is installed.
2. Install dependencies: pip install -r requirements.txt
3. Copy .env.example to .env and fill in your X API credentials.
4. Run the script: `python main.py`
5. **Testing/Saving Costs:** Run `python main.py --limit 10` to fetch only the latest 10 tweets.
6. Check the `summaries/` folder for two outputs:
   - `summary_YYYY-MM-DD.md`: Raw ranked digest.
   - `intel_report_YYYY-MM-DD.md`: Strategic AI analysis (Gemini).

### 🤖 Intelligence Layer
The tool uses Gemini 1.5 Flash to synthesize raw posts into a **Global Situation Report**.
- Ensure `GEMINI_API_KEY` is set in your `.env`.
- Uses state-of-the-art reasoning to group news into strategic themes.

### 🧪 Running Tests
This project includes automated tests to verify logic without spending API credits.
```bash
pip install -r requirements.txt
pytest
```

NOTE ON COSTS:
As of 20.02.2026, parsing approximately 800 tweets via the X API v2 costs roughly 4 USD. Gemini 1.5 Flash is used within free-tier quotas where available.

Files:
- `main.py`: Main orchestrator and entry point.
- `fetch_timeline.py`: Logic for fetching posts from X API.
- `summarize.py`: Logic for ranking and formatting chronological summaries.
- `intel_report.py`: AI synthesis layer using Gemini for strategic briefings.
- `requirements.txt`: Python package dependencies.
- `.env.example`: Template for your API credentials.
- `run_daily.ps1`: Automation script for Windows Task Scheduler.
- `tests/`: Automated test suite (unit + mock tests).
- `summaries/`: Local storage for your reports (Git-ignored).

GitHub repository: https://github.com/ebelo/x-daily-summary
