---
name: Shell Command Standards
description: Guidelines for writing cross-platform and shell-compatible terminal commands, particularly for Windows PowerShell.
---

## Purpose

To prevent syntax errors when agents execute terminal commands across different shells (PowerShell vs. Bash) and operating systems.

## When to Use

Activate this skill whenever you are preparing a `run_command` call that involves:
- Chaining multiple commands.
- Conditional execution (AND/OR).
- Environment variable setting.
- File redirection or piping.

## Instructions

### 1. Command Chaining (Sequential)

**Windows PowerShell (5.1 / Default):**
- Use the semicolon (`;`) to separate commands.
- **DO NOT** use `&&` or `||`. These will cause a `ParserError`.
- Example: `git add .; git commit -m "update"`

**Bash / PowerShell 7+:**
- Use `&&` for conditional success or `;` for unconditional sequence.

### 2. Environment Variables

**PowerShell:**
- Use `$env:VAR_NAME="value"; command`
- Example: `$env:NODE_ENV="production"; npm start`

**Bash:**
- Use `VAR_NAME=value command`

### 3. Path Handling

- Always use backslashes (`\`) for local Windows paths in commands unless the tool specifically requires forward slashes (like `git`).
- Wrap paths in quotes if they contain spaces.

### 4. Error Handling

- If a command chain fails in PowerShell, the subsequent commands might still run if separated by `;`. 
- If you need "stop on failure" behavior in PowerShell 5.1, you must run commands separately or use a script block with error checking.
