"""
run_daily.py
Cross-platform runner for the X Daily Summary Tool.

Run manually:
    python run_daily.py

Schedule with cron (macOS/Linux) — e.g. daily at 07:00:
    0 7 * * * /usr/bin/python3 /path/to/x_daily_summary/run_daily.py

Schedule with Windows Task Scheduler:
    Program: python.exe
    Arguments: C:\\path\\to\\x_daily_summary\\run_daily.py
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
MAIN_PY = SCRIPT_DIR / "main.py"


def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[run] Starting X daily summary at {now}...")

    result = subprocess.run(
        [sys.executable, str(MAIN_PY)],
        cwd=str(SCRIPT_DIR),
    )

    if result.returncode == 0:
        print("[run] Done! Check the summaries/ folder for today's digest.")
    else:
        print(f"[run] Script exited with errors (code {result.returncode}). Check the output above.")
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
