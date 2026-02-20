# run_daily.ps1
# Run the X daily summary tool.
# Schedule this with Windows Task Scheduler to automate daily runs.
#
# To schedule: open Task Scheduler → Create Basic Task → Daily → start the action:
#   Program: powershell.exe
#   Arguments: -ExecutionPolicy Bypass -File "C:\Users\emman\Antigravity-data\x_daily_summary\run_daily.ps1"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# If there's a virtual environment, activate it
$venvActivate = Join-Path $scriptDir "venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    Write-Host "[run] Activating virtual environment..."
    & $venvActivate
}

Write-Host "[run] Starting X daily summary at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')..."

python main.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "[run] Done! Check the summaries\ folder for today's digest."
}
else {
    Write-Host "[run] Script exited with errors (code $LASTEXITCODE). Check the output above."
}
