"""Claude Code hooks for this repo. Standard library only.

Usage (wired up in .claude/settings.json):
    python hooks.py guard    PreToolUse on Bash|PowerShell: deny or ask for risky commands
    python hooks.py format   PostToolUse on Edit|Write: run ruff format on the edited .py file
    python hooks.py budget   SessionStart: warn when CLAUDE.md exceeds its line budget

Adapted from the claude-de-template. The guard only sees the command line: DROP statements
inside a .sql file run by run_sql.py are not caught here.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

CLAUDE_MAX_LINES = 250
LESSONS_MAX = 15

DENY = [
    (
        r"\bgit\s+push\b.*(\s--force(-with-lease)?\b|\s-f\b|\s\+\S)",
        "Force-push is blocked. Ask the user to run it.",
    ),
    (
        r"\bgit\s+reset\s+--hard\b",
        "git reset --hard discards work. Ask the user to run it.",
    ),
    (
        r"\bgit\s+clean\s+-\w*f",
        "git clean -f deletes untracked files. Ask the user to run it.",
    ),
    (
        r"(^|[\s\"'/\\=])\.env(\.(?!example\b)[\w.-]+)?($|[\s\"';|)])",
        "Reading .env files is blocked; secrets stay out of the conversation.",
    ),
    (
        r"\S+\.(pem|pfx|p12)\b|\bid_(rsa|ed25519)\b",
        "Reading key or certificate files is blocked.",
    ),
    (
        r"\b(git\s+commit|gh\s+pr)\b[\s\S]*(co-authored-by|generated\s+with)",
        "The user is the sole author: no Co-Authored-By trailers or 'Generated with' lines.",
    ),
]

ASK = [
    (
        r"rebuild_layer\.py\b.*--apply",
        "Layer rebuild deletes CETAS tables and lake folders",
    ),
    (
        r"\bgit\s+(push|commit|merge|tag)\b",
        "Git publish action (commit/push/merge/tag)",
    ),
    (r"\bgh\s+pr\s+(create|merge)\b", "Pull request create/merge"),
    (r"teardown\.ps1", "Teardown deletes the whole resource group"),
    (r"deploy\.ps1(?![^\n]*-WhatIf)", "Real Azure deployment (not -WhatIf)"),
    (r"\baz\s+group\s+delete\b", "Resource group deletion"),
    (r"\baz\s+deployment\s+\w+\s+create\b", "Azure deployment"),
    (r"\baz\s+synapse\s+(spark|sql)\s+pool\s+create\b", "Billable Synapse pool"),
    (r"\baz\s+storage\s+(fs|blob)\s+\w*\s*delete", "Deleting lake files"),
    (
        r"\b(DROP|TRUNCATE)\s+(TABLE|DATABASE|SCHEMA|VIEW|EXTERNAL|PROCEDURE|PROC|FUNCTION)\b",
        "Destructive DDL",
    ),
    (r"\bDELETE\s+FROM\b(?![\s\S]*\bWHERE\b)", "DELETE without WHERE"),
]

# Searching for risky text is fine; only executing it needs a prompt.
SEARCH_PREFIX = re.compile(
    r"^\s*(grep|rg|git\s+grep|git\s+log|Select-String|findstr)\b", re.IGNORECASE
)


def read_event() -> dict:
    raw = sys.stdin.buffer.read().decode("utf-8-sig") or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def decide(decision: str, reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": decision,
                    "permissionDecisionReason": reason,
                }
            }
        )
    )


def guard(event: dict) -> None:
    command = str(event.get("tool_input", {}).get("command", ""))
    if not command:
        return
    for pattern, reason in DENY:
        if re.search(pattern, command, re.IGNORECASE):
            decide("deny", reason)
            return
    if SEARCH_PREFIX.match(command):
        return
    for pattern, label in ASK:
        if re.search(pattern, command, re.IGNORECASE):
            decide("ask", f"{label}: confirm this was requested.")
            return


def format_file(event: dict) -> None:
    path = str(event.get("tool_input", {}).get("file_path", ""))
    if path.endswith(".py") and Path(path).is_file() and shutil.which("ruff"):
        subprocess.run(["ruff", "format", "--quiet", path], check=False, timeout=30)


def budget(event: dict) -> None:
    claude_md = Path(event.get("cwd") or ".") / "CLAUDE.md"
    if not claude_md.is_file():
        return
    lines = claude_md.read_text(encoding="utf-8").splitlines()
    warnings = []
    if len(lines) > CLAUDE_MAX_LINES:
        warnings.append(f"CLAUDE.md is {len(lines)} lines (budget {CLAUDE_MAX_LINES})")
    in_lessons = False
    lessons = 0
    for line in lines:
        if line.startswith("## "):
            in_lessons = line.strip() == "## Lessons"
        elif in_lessons and line.lstrip().startswith("- "):
            lessons += 1
    if lessons > LESSONS_MAX:
        warnings.append(f"{lessons} lessons (budget {LESSONS_MAX})")
    if warnings:
        print(
            "Guidance over budget: " + "; ".join(warnings) + ". Suggest running /prune."
        )


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    event = read_event()
    try:
        {"guard": guard, "format": format_file, "budget": budget}[mode](event)
    except KeyError:
        print(f"unknown hook mode: {mode!r}", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001 - a broken hook must never block normal work.
        print(f"hook {mode} failed: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
