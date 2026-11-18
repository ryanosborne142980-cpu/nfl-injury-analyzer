---
description: Run the project's checks and report honestly
---

Run each check in order. If one can't run (tool missing, infra torn down), record it as
NOT RUN with the reason; never skip silently.

1. `ruff check scripts .claude/hooks` and `ruff format --check scripts .claude/hooks`
   and `python scripts/lint_sql.py` (repo SQL rules, D8; same checks as CI)
2. `az bicep build --file infra/main.bicep --stdout > $null` (compiles; writes nothing)
3. If `sql/90_checks.sql` exists and the workspace is up:
   `python scripts/run_sql.py sql/90_checks.sql`
4. If SQL for a layer changed: rerun that layer's file once and confirm row counts don't
   change (idempotency) and source = loaded + quarantined still holds.

Do not fix anything yet. Report each check as **PASS**, **FAIL** (with output), or
**NOT RUN** (with reason); say whether anything ran against live Azure; propose fixes and
ask before applying them.
