---
name: Environment & Secret Standards
description: Guidelines for managing .env files, ensuring proper encoding, and validating credentials to prevent silent failures.
---

## Purpose

To ensure that the application's configuration and secrets are handled securely and robustly, avoiding common pitfalls like encoding issues or missing placeholders.

## When to Use

Activate this skill when:
- Modifying the `.env` file or `.env.example`.
- Adding new credentials for a platform or service.
- Troubleshooting "missing" environment variables that appear to be present in the file.
- Setting up a new environment.

## Instructions

### 1. File Encoding (CRITICAL)

- **Strict UTF-8 (No BOM)**: Always ensure the `.env` file is saved as UTF-8 without a Byte Order Mark (BOM). 
- **Verifying Encoding**: If you suspect an encoding issue, use a hex dump or a tool like `Get-Content .env -Encoding Byte` in PowerShell to check for the BOM (`EF BB BF`).
- **Fixing Encoding**: If a BOM is found, rewrite the file using a method that strips it (e.g., `[System.IO.File]::WriteAllLines`).

### 2. .env.example Sync

- **Maintain Parity**: Whenever a new environment variable is introduced, immediately add a placeholder for it in `.env.example`.
- **No Real Secrets**: Never commit real credentials to `.env.example` or any other tracked file.

### 3. Credential Health Checks

- **Execution Validation**: Before starting a long-running process (like fetching 100+ posts), perform a quick "Existence Check" for required keys.
- **Verbose Debugging**: If a fetch fails for a specific source, print which specific keys from the environment are `None` or empty.
- **Source Feature Detection**: Use internal flags (e.g., `has_x = all(...)`) to gracefully skip sources that lack credentials instead of crashing, unless the source was explicitly requested.

### 4. Git Hygiene

- **.gitignore**: Ensure `.env` is always present in `.gitignore`. Never use `--force` to add it.
- **History Check**: If a secret is accidentally committed, rotate it immediately and use a tool like BFG Repo-Cleaner to strip it from the history.
