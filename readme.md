X Daily Summary Tool
====================

A simple Python tool to fetch your X (Twitter) home timeline from the past 24 hours 
and generate a structured markdown summary.

Quick Start:
1. Ensure Python is installed.
2. Install dependencies: pip install -r requirements.txt
3. Copy .env.example to .env and fill in your X API credentials.
4. Run the script: `python main.py`
5. **Testing/Saving Costs:** Run `python main.py --limit 10` to fetch only the latest 10 tweets.
6. Check the `summaries/` folder for the output.

### 🧪 Running Tests
This project includes automated tests to verify logic without spending API credits.
```bash
pip install -r requirements.txt
pytest
```

NOTE ON COSTS:
As of 20.02.2026, parsing approximately 800 tweets via the X API v2 (home timeline endpoint) costs roughly 4 USD in API credits. 

Files:
- main.py: Entry point
- fetch_timeline.py: API interaction logic
- summarize.py: Markdown formatting logic
- run_daily.ps1: PowerShell script for automation/Task Scheduler
- .env: Your private credentials (do not share!)

GitHub repository: https://github.com/ebelo/x-daily-summary
